"""Exercise hosted auth and two-user memory isolation, then delete test users."""

from __future__ import annotations

import os
import secrets

import httpx


def main() -> None:
    base = os.environ["SUPABASE_URL"].rstrip("/")
    admin_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    public_key = (
        os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ["SUPABASE_ANON_KEY"]
    )
    hosted_url = os.environ.get("HOSTED_URL", "").rstrip("/")
    admin_headers = {"apikey": admin_key, "Authorization": f"Bearer {admin_key}"}
    users: list[str] = []
    with httpx.Client(timeout=20.0) as client:
        try:
            credentials = []
            tokens = []
            for _ in range(2):
                email = f"agent-memory-smoke-{secrets.token_hex(8)}@example.com"
                password = secrets.token_urlsafe(24)
                created = client.post(
                    f"{base}/auth/v1/admin/users",
                    headers=admin_headers,
                    json={"email": email, "password": password, "email_confirm": True},
                )
                created.raise_for_status()
                users.append(created.json()["id"])
                credentials.append({"email": email, "password": password})
                login = client.post(
                    f"{base}/auth/v1/token?grant_type=password",
                    headers={"apikey": public_key},
                    json=credentials[-1],
                )
                login.raise_for_status()
                tokens.append(login.json()["access_token"])

            def rpc(token: str, name: str, body: dict):
                response = client.post(
                    f"{base}/rest/v1/rpc/{name}",
                    headers={"apikey": public_key, "Authorization": f"Bearer {token}"},
                    json=body,
                )
                response.raise_for_status()
                return response.json() if response.content else None

            session = f"memory-{secrets.token_hex(6)}"
            assert isinstance(
                rpc(
                    tokens[0],
                    "conversation_add",
                    {
                        "p_session": session,
                        "p_role": "user",
                        "p_content": "My preferred color is indigo.",
                    },
                ),
                int,
            )
            assert (
                len(rpc(tokens[0], "conversation_recent", {"p_session": session})) == 1
            )
            assert rpc(tokens[1], "conversation_recent", {"p_session": session}) == []
            assert rpc(tokens[1], "conversation_recall", {"p_query": "indigo"}) == []
            assert rpc(tokens[1], "conversation_forget", {"p_session": session}) == 0
            assert rpc(tokens[0], "conversation_forget", {"p_session": session}) == 1

            if hosted_url:
                with httpx.Client(timeout=30.0, follow_redirects=False) as web:
                    assert web.get(f"{hosted_url}/api/session").status_code == 401
                    login = web.post(
                        f"{hosted_url}/auth/login",
                        headers={"Origin": hosted_url},
                        json=credentials[1],
                    )
                    login.raise_for_status()
                    assert web.get(f"{hosted_url}/api/session").status_code == 200

                    def action(name: str, values: dict):
                        response = web.post(
                            f"{hosted_url}/api/action",
                            headers={"Origin": hosted_url},
                            json={"action": name, "values": values},
                        )
                        response.raise_for_status()
                        return response.json()["result"]

                    assert action(
                        "add",
                        {
                            "session": session,
                            "role": "user",
                            "content": "My preferred color is indigo.",
                        },
                    )["message_id"]
                    assert len(action("history", {"session": session})) == 1
                    assert len(action("recall", {"query": "indigo"})) == 1
                    answer = action(
                        "chat",
                        {"session": session, "message": "What color do I prefer?"},
                    )["answer"]
                    assert isinstance(answer, str) and answer.strip()
                    assert len(action("history", {"session": session})) == 3
                    assert (
                        action("forget", {"session": session})["deleted_messages"] == 3
                    )
            print("Two-user memory isolation and hosted actions passed")
        finally:
            for user_id in users:
                deleted = client.delete(
                    f"{base}/auth/v1/admin/users/{user_id}", headers=admin_headers
                )
                deleted.raise_for_status()


if __name__ == "__main__":
    main()
