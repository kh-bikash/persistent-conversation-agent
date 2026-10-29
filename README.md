# Persistent Conversation Agent

## About

This assistant can remember what a person has said across conversations. It saves messages under a user and session, brings back relevant earlier context, and uses that context when answering a new message. A user can inspect their history, search for a memory, and forget a session.

### What you can do

- Save and review conversations by session.
- Search memories from earlier sessions before asking a new question.
- Chat with recent and recalled context, with compression when context grows too large.
- Delete a session's messages and summary when they are no longer wanted.

The CLI and local browser are usable now with SQLite. They provide a built-in lexical embedder and an optional semantic embedding mode. A hosted Vercel version has been implemented with email and password accounts, Supabase storage, and full-text recall, but its database migration and live deployment are still pending. The hosted URL in deployment notes should not be treated as available yet.

## Quick start

Requires Python 3.11 or newer. From this repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
pytest -q
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
```

For live model calls, set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` and `OPENAI_BASE_URL` as shown in `.env.example`. The test suite uses stubs and needs no model key.

The installed `conversation-memory` command provides a durable product workflow. For example, `conversation-memory --db memory.sqlite3 --tenant alice add session-1 user "I prefer short answers"` stores a memory; replace `add` with `history session-1`, `recall "short answers"`, `chat session-1 "How should you respond?"`, or `forget session-1`. Only `chat` needs the model key with the default hashing embedder. Add `--semantic` before the command to use the configured OpenAI embedding model for semantic recall; select that mode when creating a new database and keep it consistent. To use the browser, run `conversation-memory --db memory.sqlite3 --tenant alice serve --port 8080` and open `http://127.0.0.1:8080`. The tenant is set by the server operator, not a browser form.

```python
from persistent_conversation_agent.engine import ConversationMemory
from persistent_conversation_agent.llm import OpenAICompatibleLLM

memory = ConversationMemory(
    "memory.sqlite3", OpenAICompatibleLLM.from_env(), tenant_id="user-123"
)
print(
    memory.respond("session-1", "Remember that my preferred format is bullet points.")
)
print(memory.respond("session-2", "What format do I prefer?"))
memory.forget_session("session-1")
```

## Architecture

```mermaid
flowchart LR
    CLI[Command line] --> User
    Browser[Browser interface] --> User
    User[Authenticated tenant and message] --> Memory[Conversation memory]
    Memory --> Messages[(SQLite messages)]
    Memory --> Vectors[(Vector store)]
    Memory --> Summary[(Saved summaries)]
    Messages --> Context[Recent context]
    Vectors --> Recall[Cross session recall]
    Summary --> Context
    Recall --> Context
    Context --> LLM[Response model]
    LLM --> Memory
    Memory --> Reply[Reply]
```

Hosted path:

```mermaid
flowchart LR
    Browser --> Vercel[FastAPI on Vercel]
    Vercel --> Auth[Supabase Auth]
    Vercel --> RPC[Postgres Data API RPCs]
    RPC --> RLS[Owner-scoped row policies]
    RLS --> Messages[(Messages and summaries)]
    RPC --> Search[Full-text recall]
    Vercel --> Groq[OpenAI-compatible chat API]
    Groq --> Vercel
```

| Component | Responsibility |
|---|---|
| Tenant boundary | Scopes reads and deletions by a required tenant ID. |
| Embedding adapter | Uses a local baseline or an injected semantic embedding model. |
| Context manager | Combines recent turns, vector recall, and saved compression. |

Session messages -> SQLite table and vector index -> recent window plus cross-session cosine search -> optional compression -> model -> durable reply.

See [ARCHITECTURE.md](ARCHITECTURE.md) for components, state, failure behavior, and operations.

## Deployment and safety

See [DEPLOYMENT.md](DEPLOYMENT.md) for the non-root container, token-protected browser, data mounts, and release checks.

The bundled hashing embedder is a lexical baseline; inject a semantic embedder for production recall. Every query is scoped to a required tenant ID. The integrating service must authenticate the user and derive that ID from its trusted identity system. The forget operation deletes one session's messages, vectors, and summary.

For semantic recall, pass `embedder=OpenAIEmbedding.from_env()` from `persistent_conversation_agent.embeddings` when constructing `ConversationMemory`. Rebuild an existing vector store when changing the embedding model or dimensions. SQLite performs a linear vector scan; use a dedicated vector index for large collections.

Databases created before tenant scoping require an explicit owner mapping. The library refuses to open that legacy schema so messages cannot be silently assigned to the wrong user.

Install this as a library in an authenticated application or worker. Supply the LLM adapter through dependency injection. Keep secrets in environment variables, never in source control.

## Verification

`pytest -q` runs deterministic tests. GitHub Actions runs the same suite on pushes and pull requests.
`scripts/smoke_hosted.py` creates two temporary users, checks memory isolation, exercises the hosted UI API and model, and removes both users. The script requires Supabase operator credentials in the process environment and must run only from a trusted machine.

## License

MIT. See [LICENSE](LICENSE).
