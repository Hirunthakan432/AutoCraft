from src.agent.controller import AgentController, create_agent
from src.core.memory import AgentMemory
from src.llm.provider import MockProvider
from src.security.sandbox import ToolSandbox


def test_agent_controller_without_llm():
    agent = AgentController(llm=None)
    result = agent.run("test task")
    assert result["status"] == "completed"
    assert result["task"] == "test task"
    assert "test task" in agent.memory.recall("tasks")


def test_agent_controller_with_mock_llm():
    mock = MockProvider(prefix="OK")
    agent = AgentController(llm=mock)
    response = agent.run("ship it")
    assert response == "OK: ship it"
    assert agent.memory.get_history()[-1]["role"] == "model"
    assert agent.memory.recall("responses") == ["OK: ship it"]


def test_agent_chat_multi_turn():
    mock = MockProvider()
    agent = AgentController(llm=mock)
    agent.chat("first")
    agent.chat("second")
    history = agent.memory.get_history()
    assert len(history) == 4  # user, model, user, model
    assert history[2]["content"] == "second"


def test_agent_run_tool_via_sandbox():
    sandbox = ToolSandbox()
    sandbox.register("double", lambda x: x * 2)
    agent = AgentController(llm=None, sandbox=sandbox)
    assert agent.run_tool("double", 21) == 42


def test_create_agent_mock():
    agent = create_agent(use_mock=True)
    assert isinstance(agent.llm, MockProvider)
    assert isinstance(agent.memory, AgentMemory)
