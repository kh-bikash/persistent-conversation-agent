from persistent_conversation_agent.engine import ConversationMemory


class Stub:
    def complete(self, messages, *, model=None):
        return "Remembered."


def test_cross_session_recall_and_forget(tmp_path):
    memory = ConversationMemory(tmp_path / "memory.db", Stub())
    memory.add("one", "user", "My favorite color is turquoise")
    assert memory.recall("turquoise", exclude_session="two")[0].session == "one"
    assert memory.respond("two", "What color is turquoise?") == "Remembered."
    assert len(memory.recent("two")) == 2
    assert memory.forget_session("one") == 1
    assert not memory.recall("turquoise", exclude_session="two")
