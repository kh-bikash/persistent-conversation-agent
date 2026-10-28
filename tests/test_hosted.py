"""Authenticated hosted actions and durable memory orchestration."""

from __future__ import annotations

from urllib.error import HTTPError

from fastapi.testclient import TestClient

import app as web_app
from persistent_conversation_agent import hosted


def test_web_auth_boundary(monkeypatch):
    def auth(method, path, *, token="", body=None):
        if path == "user" and token == "access":
            return {"id": "user-1", "email": "user@example.com"}
        if path == "token?grant_type=password":
            return {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 3600,
            }
        raise AssertionError((method, path))

    monkeypatch.setattr(web_app, "_auth_request", auth)
    monkeypatch.setattr(
        web_app,
        "run_action",
        lambda action, values, token: {"action": action, "token": token},
    )
    client = TestClient(web_app.app, base_url="https://memory.example.com")
    payload = {"action": "history", "values": {"session": "work"}}
    assert (
        client.post(
            "/api/action",
            json=payload,
            headers={"Origin": "https://memory.example.com"},
        ).status_code
        == 401
    )
    login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "password123"},
        headers={"Origin": "https://memory.example.com"},
    )
    assert login.status_code == 200
    assert client.post(
        "/api/action", json=payload, headers={"Origin": "https://memory.example.com"}
    ).json() == {"result": {"action": "history", "token": "access"}}

    def provider_down(action, values, token):
        raise HTTPError("https://model.example", 403, "blocked", {}, None)

    monkeypatch.setattr(web_app, "run_action", provider_down)
    assert (
        client.post(
            "/api/action",
            json=payload,
            headers={"Origin": "https://memory.example.com"},
        ).status_code
        == 503
    )


def test_chat_appends_exchange_after_answer(monkeypatch):
    calls = []

    def rpc(name, values, token):
        calls.append((name, values, token))
        return {
            "conversation_recent": [],
            "conversation_recall": [],
            "conversation_get_summary": [],
        }.get(name, {"user_id": 1, "assistant_id": 2})

    class FakeLLM:
        def complete(self, messages):
            assert messages[-1] == {"role": "user", "content": "Hello"}
            return "Hi there"

    monkeypatch.setattr(hosted, "_rpc", rpc)
    monkeypatch.setattr(hosted.OpenAICompatibleLLM, "from_env", lambda: FakeLLM())
    assert hosted.run_action(
        "chat", {"session": "work", "message": "Hello"}, "jwt"
    ) == {"answer": "Hi there"}
    assert calls[-1] == (
        "conversation_append_exchange",
        {"p_session": "work", "p_user": "Hello", "p_assistant": "Hi there"},
        "jwt",
    )


def test_rejects_invalid_memory_input():
    try:
        hosted.run_action(
            "add", {"session": "work", "role": "system", "content": "x"}, "jwt"
        )
    except ValueError as exc:
        assert "Role" in str(exc)
    else:
        raise AssertionError("Expected invalid role to fail")
