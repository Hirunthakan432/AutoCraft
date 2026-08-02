from src.agent.orchestrator import MultiAgentOrchestrator, create_team
from src.agent.roles import DEFAULT_PIPELINE, DEFAULT_ROLES
from src.llm.provider import MockProvider


def test_default_roles_registered():
    team = create_team(use_mock=True)
    names = {r["name"] for r in team.list_roles()}
    assert names >= {"planner", "coder", "reviewer"}


def test_pipeline_runs_all_roles():
    team = MultiAgentOrchestrator(
        shared_llm=MockProvider(prefix="Step"),
        pipeline=("planner", "coder", "reviewer"),
    )
    result = team.run("Build a hello world API")
    assert result.goal == "Build a hello world API"
    assert [s.role for s in result.steps] == ["planner", "coder", "reviewer"]
    assert result.final.startswith("Step:")
    # Later agents see earlier outputs in their prompt
    assert "PLANNER output" in result.steps[1].input
    assert "CODER output" in result.steps[2].input


def test_custom_pipeline():
    team = MultiAgentOrchestrator(
        shared_llm=MockProvider(),
        pipeline=("researcher",),
    )
    result = team.run("Investigate caching")
    assert len(result.steps) == 1
    assert result.steps[0].role == "researcher"


def test_run_role_single():
    team = create_team(use_mock=True)
    out = team.run_role("planner", "Ship auth")
    assert isinstance(out, str)
    assert len(out) > 0


def test_unknown_role_raises():
    team = MultiAgentOrchestrator(shared_llm=MockProvider())
    try:
        team.run("x", pipeline=("nope",))
        assert False, "expected KeyError"
    except KeyError as e:
        assert "nope" in str(e)


def test_result_to_dict():
    team = create_team(use_mock=True)
    d = team.run("goal").to_dict()
    assert "goal" in d and "steps" in d and "final" in d
    assert len(d["steps"]) == len(DEFAULT_PIPELINE)
