from src.agent.controller import AgentController


def test_agent_controller_runs_task():
    agent = AgentController()
    result = agent.run("test task")

    assert result["status"] == "completed"
