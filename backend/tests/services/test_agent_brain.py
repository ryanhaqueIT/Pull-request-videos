"""Tests for the agent brain — Claude-powered reasoning loop."""

from unittest.mock import AsyncMock, patch

import pytest

from models.agent import (
    AgentSession,
    AgentStatus,
    InteractionPlan,
    InteractionStep,
    StepType,
)
from services.agent_brain import AgentBrain
from services.interaction import InteractionResult


@pytest.fixture
def session() -> AgentSession:
    return AgentSession(
        session_id="test-1",
        repo_url="https://github.com/test/repo",
        diff="+ <button id='submit'>Submit</button>",
        app_url="http://localhost:3000",
    )


@pytest.fixture
def mock_plan() -> InteractionPlan:
    return InteractionPlan(
        description="Test submit button",
        steps=[
            InteractionStep(step_type=StepType.NAVIGATE, target="http://localhost:3000"),
            InteractionStep(step_type=StepType.CLICK, selector="button#submit"),
            InteractionStep(step_type=StepType.SCREENSHOT, description="after click"),
        ],
    )


@pytest.mark.asyncio
async def test_agent_brain_plan_phase(session: AgentSession, mock_plan: InteractionPlan) -> None:
    mock_gateway = AsyncMock()
    mock_gateway.generate_interaction_plan = AsyncMock(return_value=mock_plan)

    brain = AgentBrain(gateway=mock_gateway, session=session)
    plan = await brain.plan()

    assert plan is not None
    assert len(plan.steps) == 3
    assert session.status == AgentStatus.PLANNING
    assert len(session.actions) == 1
    assert "3 steps" in session.actions[0].description


@pytest.mark.asyncio
async def test_agent_brain_execute_phase(session: AgentSession, mock_plan: InteractionPlan) -> None:
    mock_gateway = AsyncMock()
    brain = AgentBrain(gateway=mock_gateway, session=session)
    session.interaction_plan = mock_plan

    mock_result = InteractionResult(steps_completed=3, total_steps=3, screenshots=["/tmp/s1.png"])
    with patch(
        "services.agent_brain.execute_interaction_plan",
        return_value=mock_result,
    ):
        result = await brain.execute()

    assert result.steps_completed == 3
    assert session.status == AgentStatus.INTERACTING


@pytest.mark.asyncio
async def test_agent_brain_execute_without_plan(session: AgentSession) -> None:
    mock_gateway = AsyncMock()
    brain = AgentBrain(gateway=mock_gateway, session=session)

    with pytest.raises(ValueError, match="No interaction plan"):
        await brain.execute()


def test_agent_brain_generates_summary(session: AgentSession) -> None:
    mock_gateway = AsyncMock()
    brain = AgentBrain(gateway=mock_gateway, session=session)

    result = InteractionResult(
        steps_completed=3,
        total_steps=3,
        screenshots=["/tmp/s.png"],
        duration_seconds=5.2,
    )
    summary = brain.generate_summary(result)

    assert "3/3" in summary
    assert "Agent Demo Summary" in summary
    assert "5.2s" in summary


def test_agent_brain_summary_with_errors(session: AgentSession) -> None:
    mock_gateway = AsyncMock()
    brain = AgentBrain(gateway=mock_gateway, session=session)

    result = InteractionResult(
        steps_completed=2,
        total_steps=3,
        screenshots=[],
        errors=["Button not found"],
        duration_seconds=3.0,
    )
    summary = brain.generate_summary(result)

    assert "2/3" in summary
    assert "Button not found" in summary
    assert "Issues encountered" in summary
