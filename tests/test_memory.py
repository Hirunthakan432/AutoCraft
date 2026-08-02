from src.core.memory import AgentMemory, ConversationMemory


def test_conversation_roundtrip():
    mem = AgentMemory(system_instruction="sys")
    mem.add_user_message("hi")
    mem.add_agent_message("hello")
    history = mem.get_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["content"] == "hello"


def test_facts_remember_recall():
    mem = AgentMemory()
    mem.remember("tasks", "build feature")
    mem.remember("tasks", "write tests")
    assert mem.recall("tasks") == ["build feature", "write tests"]
    assert mem.recall("missing") == []


def test_clear_separates_history_and_facts():
    mem = AgentMemory()
    mem.add_user_message("x")
    mem.remember("k", "v")
    mem.clear_history()
    assert mem.get_history() == []
    assert mem.recall("k") == ["v"]
    mem.clear()
    assert mem.recall("k") == []


def test_conversation_memory_alias():
    assert ConversationMemory is AgentMemory
