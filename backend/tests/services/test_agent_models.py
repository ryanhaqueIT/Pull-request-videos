"""Tests for agent data models."""

from models.agent import (
    AgentAction,
    AgentActionType,
    AgentSession,
    AgentStatus,
    InteractionPlan,
    InteractionStep,
    StepType,
)


def test_agent_session_defaults() -> None:
    session = AgentSession(session_id="s1", repo_url="https://github.com/test/repo")
    assert session.status == AgentStatus.PENDING
    assert session.actions == []
    assert session.error == ""


def test_interaction_plan_from_steps() -> None:
    steps = [
        InteractionStep(step_type=StepType.NAVIGATE, target="http://localhost:3000"),
        InteractionStep(step_type=StepType.CLICK, selector="button#submit"),
        InteractionStep(step_type=StepType.SCREENSHOT, description="after click"),
    ]
    plan = InteractionPlan(steps=steps, description="Test the submit button")
    assert len(plan.steps) == 3
    assert plan.steps[0].step_type == StepType.NAVIGATE


def test_agent_action_records_result() -> None:
    action = AgentAction(
        action_type=AgentActionType.EXECUTE_PLAN,
        description="Run interaction plan",
        result="3 steps completed",
    )
    assert action.action_type == AgentActionType.EXECUTE_PLAN
