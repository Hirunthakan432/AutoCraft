from src.agent.tester import TestingAgent
from src.llm.provider import MockProvider
from src.agent.controller import AgentController


def test_plan_only():
    agent = AgentController(llm=MockProvider(prefix="PLAN"))
    tester = TestingAgent(agent=agent)
    result = tester.run("cover memory module", execute=False)
    assert "PLAN:" in result.plan or result.plan
    assert result.command.startswith("pytest")
    assert result.passed is None
    assert any("execute=False" in n for n in result.notes)


def test_run_pytest_via_sandbox():
    agent = AgentController(llm=MockProvider(prefix="COMMAND: pytest -q"))
    # Force plan text to include COMMAND line via mock returning that string
    agent.llm = MockProvider(prefix="Use\nCOMMAND: pytest -q")
    tester = TestingAgent(agent=agent)
    result = tester.run("run unit tests", execute=True)
    assert result.command_output  # sandbox produced output
    assert "Exit Code" in result.command_output


def test_extract_pytest_args_variants():
    assert TestingAgent._extract_pytest_args("pytest -q") == "-q"
    assert TestingAgent._extract_pytest_args("python -m pytest -v tests/") == "-v tests/"
    assert TestingAgent._extract_pytest_args("python3 -m pytest") == "-q"
    assert TestingAgent._extract_pytest_args("rm -rf /") is None
