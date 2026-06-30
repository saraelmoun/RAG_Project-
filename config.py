"""Configuration centrale du projet RAG.

Source unique de verite lue par tous les scripts (cf. CLAUDE.md).
Les valeurs sensibles a l'environnement (URL, DSN) sont surchargeables
par variables d'environnement, sans modifier le code.
"""

import os

# --- Modeles (doivent correspondre EXACTEMENT a CLAUDE.md) ---
EMBED_MODEL = "bge-m3"          # embedding, 1024 dimensions
EMBED_DIM = 1024                # = colonne pgvector vector(1024)
GEN_MODEL = "llama3.1:8b"       # generation

# --- Chunking ---
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# --- Recuperation (retrieval) ---
TOP_K = 4                       # nb de passages ramenes par defaut a la requete

# --- Connexions (override possible via env) ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DB_DSN = os.environ.get("DB_DSN", "postgresql://rag:rag@localhost:5432/ragdb")
