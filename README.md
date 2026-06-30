# RAG Project

Projet de Retrieval-Augmented Generation (RAG).

## Reproduire

Pile 100 % locale (Ollama + pgvector via Docker). Dans l'ordre :

1. **Démarrer l'infra** — `make up`
   (ou `make up-gpu` pour réserver les GPU nvidia à Ollama)
2. **Télécharger les modèles** — `make pull`
   (récupère `bge-m3` pour l'embedding et `llama3.1:8b` pour la génération)
3. **Ingestion** — *(phase suivante : scripts dans `ingest/`)*
4. **Requête** — *(phase suivante : scripts dans `query/`)*
5. **Évaluation** — *(phase suivante : scripts dans `eval/`, résultats dans `results/`)*

Repartir de zéro (supprime les volumes db + ollama) : `make reset`

> La dimension pgvector `vector(1024)`, les noms de modèles et les paramètres de
> chunking sont définis **uniquement** dans `config.py` (cf. `CLAUDE.md`).
