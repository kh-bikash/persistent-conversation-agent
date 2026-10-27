# Architecture

## Goal

Store conversations in SQLite, recall earlier messages by vector similarity, and compress oversized context.

## Request path

Session messages -> SQLite table and vector index -> recent window plus cross-session cosine search -> optional compression -> model -> durable reply.

## Components

- `src/persistent_conversation_agent/engine.py`: policy and state transitions for this project.
- `src/persistent_conversation_agent/llm.py`: injected model protocol and HTTPS OpenAI-compatible adapter with timeouts and retry for transient transport failures.
- `tests/test_engine.py`: deterministic behavior and failure tests.
- `.github/workflows/ci.yml`: install and test gate.


## State and failure behavior

The bundled hashing embedder is a lexical baseline; inject a semantic embedder for production recall. Every query is scoped to a required tenant ID. The integrating service must authenticate the user and derive that ID from its trusted identity system. The forget operation deletes one session's messages, vectors, and summary.

The LLM adapter times out after 30 seconds and retries transient HTTP failures twice. Model output is untrusted input and is parsed or validated at the project boundary.

## Operations checklist

1. Set secrets through a secret manager and rotate them regularly.
2. Put the service or integrating application behind TLS and authentication.
3. Persist SQLite files on durable storage and back them up; migrate to a managed database for high write volume or multiple replicas.
4. Run `pytest -q` in CI before deployment.
5. Define workload specific evaluation cases, latency objectives, and rollback criteria before serving real users.

## Data model and isolation

SQLite stores `messages(tenant,session,role,content,created_at)`, `vectors(message_id,vector)`, and `summaries(tenant,session,through_id,content)`. The constructor requires a tenant ID. Every recent, recall, and delete query filters by that ID. The integrating service must derive it from authenticated identity rather than trusting a user supplied string.

The default hashing embedder is a dependency free lexical baseline. `OpenAIEmbedding` supplies semantic vectors through a live embeddings API. `metadata` records the embedding model ID and rejects a different model on an existing store, because incompatible vector spaces produce misleading recall. Recall computes cosine similarity over stored normalized vectors; this is a linear scan suitable for modest single node collections. Oversized context is summarized and saved as a checkpoint. `forget_session` deletes messages, vectors, and that summary.

For high volume collections, replace the scan with a vector index. For regulatory deletion, also address database backups and provider retention policy.
