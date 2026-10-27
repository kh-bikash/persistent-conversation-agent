import pytest

from persistent_conversation_agent.engine import ConversationMemory, HashingEmbedder


class Stub:
    def complete(self, messages, *, model=None):
        return "Remembered."


def test_cross_session_recall_and_forget(tmp_path):
    memory = ConversationMemory(tmp_path / "memory.db", Stub(), tenant_id="user-1")
    memory.add("one", "user", "My favorite color is turquoise")
    assert memory.recall("turquoise", exclude_session="two")[0].session == "one"
    assert memory.respond("two", "What color is turquoise?") == "Remembered."
    assert len(memory.recent("two")) == 2
    assert memory.forget_session("one") == 1
    assert not memory.recall("turquoise", exclude_session="two")


def test_tenant_isolation(tmp_path):
    db = tmp_path / "memory.db"
    first = ConversationMemory(db, Stub(), tenant_id="user-1")
    second = ConversationMemory(db, Stub(), tenant_id="user-2")
    first.add("shared", "user", "my secret color is turquoise")
    assert second.recent("shared") == []
    assert second.recall("turquoise") == []
    assert second.forget_session("shared") == 0
    assert first.recall("turquoise")


def test_rejects_embedding_model_change(tmp_path):
    db = tmp_path / "memory.db"
    ConversationMemory(db, Stub(), tenant_id="user-1", embedder=HashingEmbedder(64))
    with pytest.raises(ValueError, match="Embedding model differs"):
        ConversationMemory(
            db, Stub(), tenant_id="user-1", embedder=HashingEmbedder(128)
        )
