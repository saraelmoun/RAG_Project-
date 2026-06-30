"""Pipeline de requete d'un RAG EXPLICABLE (Phase 3).

Prend une question, recupere les passages les plus proches dans pgvector (similarite
cosinus), genere une reponse strictement fondee sur ces passages via llama3.1, et
AFFICHE les sources utilisees (tracabilite = coeur du projet).

Toute la config vient de config.py (rien en dur).

Lancer depuis la racine du projet :
    PYTHONPATH=. python query/query.py "ma question ?" [--k N]
(ou simplement :  make query Q="ma question ?")
"""

import argparse

import config
from ingest.ingest import get_embedder  # reutilise la logique d'embedding (anti-duplication)

import psycopg
from pgvector.psycopg import register_vector, Vector
from langchain_ollama import OllamaLLM


# Phrase exacte de repli quand l'info n'est pas dans le contexte (anti-hallucination).
NO_ANSWER = "Je n'ai pas cette information dans mes documents."

PROMPT_TEMPLATE = """Tu es un assistant qui repond a partir de documents internes.
Reponds UNIQUEMENT a partir du CONTEXTE ci-dessous.
Si l'information ne figure pas dans le contexte, reponds EXACTEMENT : "{no_answer}"
N'invente rien, ne completes pas avec des connaissances generales.

CONTEXTE :
{context}

QUESTION : {question}

REPONSE :"""


def get_llm():
    """LLM Ollama configure (llama3.1). Partage entre CLI, requete RAG et branche sans RAG."""
    return OllamaLLM(
        model=config.GEN_MODEL, base_url=config.OLLAMA_URL, temperature=0
    )


def retrieve(conn, question_vec, k):
    """Retourne les k passages les plus proches (source, content, distance cosinus)."""
    # Enveloppe dans Vector pour que le parametre soit envoye comme type `vector`
    # (sinon une liste Python part en double precision[] et l'operateur <=> echoue).
    qvec = Vector(question_vec)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT source, content, embedding <=> %s AS distance
            FROM chunks
            ORDER BY embedding <=> %s
            LIMIT %s;
            """,
            (qvec, qvec, k),
        )
        return cur.fetchall()


def build_prompt(question, passages):
    """Assemble le CONTEXTE (chaque passage prefixe de sa source) + la consigne stricte."""
    blocs = [
        f"[source: {source}]\n{content}" for source, content, _ in passages
    ]
    context = "\n\n---\n\n".join(blocs)
    return PROMPT_TEMPLATE.format(
        no_answer=NO_ANSWER, context=context, question=question
    )


def source_rows(passages):
    """Genere (rang, source, distance, extrait~150) pour chaque passage.

    Unique endroit ou vit la logique d'extrait => CLI et UI restent coherents.
    """
    for i, (source, content, distance) in enumerate(passages, start=1):
        extrait = " ".join(content.split())[:150]
        yield i, source, distance, extrait


def answer_with_rag(question, k=config.TOP_K):
    """Pipeline RAG complet : retourne (reponse, passages). 0 passage => (NO_ANSWER, [])."""
    vec = get_embedder().embed_query(question)
    if len(vec) != config.EMBED_DIM:
        raise ValueError(
            f"Embedding de dimension {len(vec)}, attendu {config.EMBED_DIM} "
            f"(modele {config.EMBED_MODEL})."
        )

    with psycopg.connect(config.DB_DSN) as conn:
        register_vector(conn)
        passages = retrieve(conn, vec, k)

    if not passages:
        return NO_ANSWER, []

    prompt = build_prompt(question, passages)
    answer = get_llm().invoke(prompt)
    return answer, passages


def answer_without_rag(question):
    """Branche 'Sans RAG' : llama3.1 SEUL, juste la question, aucun contexte."""
    return get_llm().invoke(question)


def render(question, answer, passages, k):
    """Affichage lisible : reponse PUIS sources (partie explicable)."""
    print()
    print(f"Question : {question}")
    print(f"Reponse  : {answer.strip()}")
    print()
    print("Sources :")
    if not passages:
        print("  (aucun passage trouve dans la base)")
    for i, source, distance, extrait in source_rows(passages):
        print(f"  [{i}] {source} (distance {distance:.4f})")
        print(f'      "{extrait}..."')
    print()
    print(
        f"Config : modele_gen={config.GEN_MODEL} modele_embed={config.EMBED_MODEL} "
        f"dim={config.EMBED_DIM} k={k}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Requete RAG explicable : repond a une question et cite ses sources."
    )
    parser.add_argument("question", help="La question a poser (entre guillemets).")
    parser.add_argument(
        "--k",
        type=int,
        default=config.TOP_K,
        help=f"Nombre de passages a recuperer (defaut {config.TOP_K}, depuis config.py).",
    )
    args = parser.parse_args()

    question = args.question.strip()
    if not question:
        parser.error("La question est vide.")

    answer, passages = answer_with_rag(question, args.k)
    render(question, answer, passages, args.k)


if __name__ == "__main__":
    main()
