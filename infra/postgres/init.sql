-- Runs once, on first container start, before any Alembic migration (see
-- docs/DECISIONS.md "Audit-only DB role"). Enables the extensions the app
-- needs across every phase: pgvector for RAG embeddings (§14/§21 aph_chunks),
-- pgcrypto for gen_random_uuid() primary keys (§21 conventions).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
