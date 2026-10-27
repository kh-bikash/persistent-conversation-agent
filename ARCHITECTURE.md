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

The bundled hashing embedder is a lexical baseline; inject a semantic embedder for production recall. This example assumes one user's sessions. Add a tenant/user column and enforce it in every query before using a shared multi-user service. The forget operation deletes one session's messages and vectors.

The LLM adapter times out after 30 seconds and retries transient HTTP failures twice. Model output is untrusted input and is parsed or validated at the project boundary.

## Operations checklist

1. Set secrets through a secret manager and rotate them regularly.
2. Put the service or integrating application behind TLS and authentication.
3. Persist SQLite files on durable storage and back them up; migrate to a managed database for high write volume or multiple replicas.
4. Run `pytest -q` in CI before deployment.
5. Define workload specific evaluation cases, latency objectives, and rollback criteria before serving real users.
