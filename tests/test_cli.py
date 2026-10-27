import json

from persistent_conversation_agent.__main__ import main


def test_cli_persists_and_forgets_a_session(tmp_path, capsys):
    prefix = ["--db", str(tmp_path / "memory.sqlite3"), "--tenant", "alice"]
    assert main(prefix + ["add", "s1", "user", "Please be concise"]) == 0
    capsys.readouterr()
    assert main(prefix + ["history", "s1"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["content"] == "Please be concise"
    assert main(prefix + ["forget", "s1"]) == 0
    assert json.loads(capsys.readouterr().out)["deleted_messages"] == 1


def test_cli_chat_persists_model_reply(tmp_path, monkeypatch, capsys):
    class FakeLLM:
        def complete(self, messages, *, model=None):
            return "I will keep answers concise."

    monkeypatch.setattr(
        "persistent_conversation_agent.__main__.OpenAICompatibleLLM.from_env",
        lambda: FakeLLM(),
    )
    prefix = ["--db", str(tmp_path / "memory.sqlite3"), "--tenant", "alice"]
    assert main(prefix + ["chat", "s1", "Please be concise"]) == 0
    assert "concise" in json.loads(capsys.readouterr().out)["answer"]
    assert main(prefix + ["history", "s1"]) == 0
    assert [m["role"] for m in json.loads(capsys.readouterr().out)] == [
        "user",
        "assistant",
    ]
