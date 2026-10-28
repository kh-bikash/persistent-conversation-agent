# Deployment

## Hosted Vercel and Supabase product

The shared schema migrations live in the separate `agent-suite-platform` repository. Apply `20261028123835_conversation_messages.sql` there before deployment. Connect this Vercel project to the shared Supabase integration. Required environment variables are `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` (or `SUPABASE_ANON_KEY`), `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`. Keep the database password and service-role key out of this app's browser and runtime. Vercel's integration can inject them, but application code does not use them.

Deploy with `vercel deploy --prod`. Verify `/healthz`, sign-up and confirmation, sign-in, `add`, `history`, `recall`, `chat`, and `forget` through the hosted URL. Run `scripts/smoke_hosted.py` from a trusted machine with operator credentials; it tests two-user RLS isolation and cleans up its test accounts. The hosted product uses Postgres full-text search for recall; the local vector index remains available to CLI users. The default Supabase mail service and a free model tier have low quotas, so configure capacity and mail delivery before a broad launch.

## Local product

Install with `python -m pip install -e .`, then run the command shown in README. The browser binds to `127.0.0.1:8080` by default. `GET /healthz` is a lightweight health endpoint.

## Container

Copy `.env.example` to `.env`, replace every example secret, and keep that file outside Git. Build and run from this repository:

```bash
docker build -t persistent-conversation-agent .
docker run --rm -p 127.0.0.1:8080:8080 --env-file .env -v conversation_memory_data:/data persistent-conversation-agent --db /data/memory.sqlite3 --tenant operator serve --port 8080
```

The image runs as a non-root user. It binds inside the container to `0.0.0.0`; the example publishes only to host loopback. A non-loopback bind requires `AGENT_WEB_TOKEN` of at least 16 characters. The browser asks for that token and sends it to the action endpoint. Put TLS and an authenticated reverse proxy in front of any public deployment.

Back up the volume. This browser instance serves one configured tenant; run separate authenticated instances or integrate the library with tenant-aware authentication for multiple users. Set OPENAI_API_KEY for chat.
For semantic retrieval, add `--semantic` before `serve` on the first launch of a new database and configure `EMBEDDING_MODEL`. Do not switch embedding models on an existing database without rebuilding its vectors.

## Release checks

Run `ruff check .`, `ruff format --check .`, and `pytest -q`. Test the browser action path and `/healthz` after deployment. Keep secrets in the deployment platform, monitor failed actions and model/provider errors, and set backups for any mounted data volume.
