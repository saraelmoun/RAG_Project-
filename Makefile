.PHONY: up up-gpu pull ingest query app reset

# Demarre la pile (db + ollama)
up:
	docker compose up -d

# Demarre la pile avec reservation GPU nvidia pour ollama
up-gpu:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# Telecharge les modeles dans le conteneur ollama
pull:
	docker compose exec ollama ollama pull bge-m3
	docker compose exec ollama ollama pull llama3.1:8b

# Ingestion du corpus dans la table chunks (lit toute la config depuis config.py)
ingest:
	PYTHONPATH=. python ingest/ingest.py

# Requete RAG explicable : make query Q="ma question ?"
query:
	PYTHONPATH=. python query/query.py "$(Q)"

# Lance l'interface Gradio (exploration visuelle du RAG)
app:
	PYTHONPATH=. python app.py

# Arrete tout et supprime les volumes (repart de zero => re-ingestion propre)
reset:
	docker compose down -v
