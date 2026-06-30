# Projet RAG — conventions (à respecter à chaque session)

## Stack
- Tout en local. LLM via Ollama. Aucun secret / clé d'API dans le repo ou les conteneurs.
- Génération : llama3.1:8b. Embedding : bge-m3 (1024 dim).
- Infra unique : docker-compose.yml. Ne jamais lancer un conteneur à la main hors compose.

## Base vectorielle (invariant critique)
- La colonne pgvector est vector(1024) = dimension de bge-m3.
- Changer de modèle d'embedding => changer N => ré-ingestion obligatoire.
- Comparer 2 modèles => tables versionnées (chunks_bge_m3, chunks_nomic), jamais d'écrasement.

## Pipelines
- Ingestion idempotente (clé sur le hash du chunk, pas de doublon).
- Améliorations (hybride, rerank) = flags activables, pour produire baseline vs amélioré
  dans les mêmes conditions (table d'ablation valide).
- Toute exécution de mesure logge sa config (modèle, k, chunking) à côté des résultats.

## Config centrale
- modèle, dimension, taille de chunk, overlap : uniquement dans config.py, lu par tous les scripts.
