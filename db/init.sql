-- Initialisation de la base vectorielle (executee une seule fois au premier demarrage).
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT,
    chunk_hash  TEXT UNIQUE,        -- idempotence d'ingestion (CLAUDE.md)
    content     TEXT,
    embedding   vector(1024)        -- = EMBED_DIM (bge-m3) : invariant critique
);
