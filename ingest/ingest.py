"""Pipeline d'ingestion du corpus dans la table `chunks` (Phase 2).

Lit corpus/, decoupe en chunks, calcule l'embedding via Ollama (bge-m3) et insere
de facon idempotente. Toute la configuration vient de config.py (rien en dur).

Lancer depuis la racine du projet :  PYTHONPATH=. python ingest/ingest.py
(ou simplement :  make ingest)
"""

import glob
import hashlib
import os

import config
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings

import psycopg
from pgvector.psycopg import register_vector

# Racine du projet = dossier parent de ingest/, pour resoudre corpus/ quel que soit le cwd.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(ROOT, "corpus")


def get_embedder():
    """Embedder Ollama configure (bge-m3). Partage entre ingestion et requete."""
    return OllamaEmbeddings(model=config.EMBED_MODEL, base_url=config.OLLAMA_URL)


def read_corpus():
    """Retourne une liste de (source, texte_brut) pour chaque .md du corpus."""
    documents = []
    for path in sorted(glob.glob(os.path.join(CORPUS_DIR, "*.md"))):
        source = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            documents.append((source, f.read()))
    return documents


def chunk_documents(documents):
    """Decoupe chaque document en chunks. Retourne une liste de dicts traçables."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for source, text in documents:
        for piece in splitter.split_text(text):
            content = piece.strip()
            if not content:
                continue
            # Hash stable sur (source + contenu) => 1 ligne par (fichier, chunk),
            # tracabilite de la source garantie (RAG explicable).
            chunk_hash = hashlib.sha256(
                f"{source}\n{content}".encode("utf-8")
            ).hexdigest()
            chunks.append(
                {"source": source, "content": content, "chunk_hash": chunk_hash}
            )
    return chunks


def existing_hashes(conn):
    """Set des chunk_hash deja presents en base (pour eviter de re-embedder)."""
    with conn.cursor() as cur:
        cur.execute("SELECT chunk_hash FROM chunks;")
        return {row[0] for row in cur.fetchall()}


def clear_chunks(conn):
    """Vide entierement la table chunks (cas UI : un seul corpus a la fois)."""
    with conn.cursor() as cur:
        cur.execute("TRUNCATE chunks RESTART IDENTITY;")


def ingest_documents(documents, reset=False):
    """Ingere une liste de (source, texte) dans la table chunks.

    Coeur reutilisable par le CLI ET l'interface Gradio (aucune lecture disque ici).
    - reset=True : vide d'abord la table (remplace le corpus).
    - Idempotent : seuls les chunks absents sont embeddes/inseres (ON CONFLICT DO NOTHING).
    Retourne un dict de stats : {files, chunks, inserted, ignored}.
    """
    chunks = chunk_documents(documents)
    n_files, n_chunks = len(documents), len(chunks)
    inserted = 0

    with psycopg.connect(config.DB_DSN) as conn:
        register_vector(conn)

        if reset:
            clear_chunks(conn)

        # Idempotence : on n'embedde QUE les chunks absents de la base.
        already = existing_hashes(conn)
        new_chunks = [c for c in chunks if c["chunk_hash"] not in already]

        if new_chunks:
            emb = get_embedder()
            vectors = emb.embed_documents([c["content"] for c in new_chunks])

            # Garde-fou invariant critique : la dimension DOIT valoir EMBED_DIM (1024).
            dim = len(vectors[0])
            if dim != config.EMBED_DIM:
                raise ValueError(
                    f"Embedding de dimension {dim}, attendu {config.EMBED_DIM} "
                    f"(modele {config.EMBED_MODEL}). Abandon, aucune insertion."
                )

            with conn.cursor() as cur:
                for c, vec in zip(new_chunks, vectors):
                    cur.execute(
                        """
                        INSERT INTO chunks (source, chunk_hash, content, embedding)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (chunk_hash) DO NOTHING;
                        """,
                        (c["source"], c["chunk_hash"], c["content"], vec),
                    )
                    inserted += cur.rowcount
            conn.commit()

    return {
        "files": n_files,
        "chunks": n_chunks,
        "inserted": inserted,
        "ignored": n_chunks - inserted,
    }


def main():
    documents = read_corpus()
    if not documents:
        print("Aucun fichier dans corpus/. Rien a faire.")
        return

    stats = ingest_documents(documents)  # CLI : append idempotent (reset=False)

    # Log final : resultats + config utilisee (exigence CLAUDE.md).
    print("--- Ingestion terminee ---")
    print(f"Fichiers lus            : {stats['files']}")
    print(f"Chunks generes          : {stats['chunks']}")
    print(f"Inseres                 : {stats['inserted']}")
    print(f"Ignores (deja presents) : {stats['ignored']}")
    print(
        f"Config : modele={config.EMBED_MODEL} dim={config.EMBED_DIM} "
        f"chunk_size={config.CHUNK_SIZE} overlap={config.CHUNK_OVERLAP}"
    )


if __name__ == "__main__":
    main()
