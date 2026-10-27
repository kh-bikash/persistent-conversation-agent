"""Durable, tenant-scoped conversation CLI and local browser interface."""

from __future__ import annotations

import argparse
import json

from .embeddings import OpenAIEmbedding
from .engine import ConversationMemory
from .llm import OpenAICompatibleLLM
from .web import serve

WEB_ACTIONS = {
    "chat": [
        ("session", "Session ID", "text", True),
        ("message", "Message", "textarea", True),
    ],
    "add": [
        ("session", "Session ID", "text", True),
        ("role", "Role: user, assistant, or summary", "text", True),
        ("content", "Content", "textarea", True),
    ],
    "history": [("session", "Session ID", "text", True)],
    "recall": [("query", "Search query", "text", True)],
    "forget": [("session", "Session ID", "text", True)],
}


class _OfflineLLM:
    def complete(self, messages, *, model=None):
        raise RuntimeError("Set OPENAI_API_KEY before using chat")


def execute(
    action: str, values: dict, *, db: str, tenant: str, semantic: bool = False
) -> object:
    llm = OpenAICompatibleLLM.from_env() if action == "chat" else _OfflineLLM()
    embedder = OpenAIEmbedding.from_env() if semantic else None
    memory = ConversationMemory(db, llm, tenant_id=tenant, embedder=embedder)
    if action == "chat":
        return {"answer": memory.respond(values["session"], values["message"])}
    if action == "add":
        return {
            "message_id": memory.add(
                values["session"], values["role"], values["content"]
            )
        }
    if action == "history":
        return [m.__dict__ for m in memory.recent(values["session"])]
    if action == "recall":
        return [m.__dict__ for m in memory.recall(values["query"])]
    if action == "forget":
        return {"deleted_messages": memory.forget_session(values["session"])}
    raise ValueError("unknown action")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tenant-scoped conversation memory")
    parser.add_argument("--db", default="memory.sqlite3")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--semantic", action="store_true", help="Use model embeddings")
    commands = parser.add_subparsers(dest="command", required=True)
    chat = commands.add_parser("chat")
    chat.add_argument("session")
    chat.add_argument("message")
    add = commands.add_parser("add")
    add.add_argument("session")
    add.add_argument("role", choices=["user", "assistant", "summary"])
    add.add_argument("content")
    history = commands.add_parser("history")
    history.add_argument("session")
    recall = commands.add_parser("recall")
    recall.add_argument("query")
    forget = commands.add_parser("forget")
    forget.add_argument("session")
    browser = commands.add_parser("serve")
    browser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    if args.command == "serve":
        serve(
            "Conversation Memory",
            WEB_ACTIONS,
            lambda action, values: execute(
                action, values, db=args.db, tenant=args.tenant, semantic=args.semantic
            ),
            port=args.port,
        )
    else:
        print(
            json.dumps(
                execute(
                    args.command,
                    vars(args),
                    db=args.db,
                    tenant=args.tenant,
                    semantic=args.semantic,
                ),
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
