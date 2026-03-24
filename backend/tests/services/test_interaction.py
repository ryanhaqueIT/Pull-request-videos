"""Tests for the Playwright interaction service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.agent import InteractionPlan, InteractionStep, StepType
from services.interaction import InteractionResult, execute_interaction_plan


@pytest.fixture
def simple_plan() -> InteractionPlan:
    return InteractionPlan(
        description="Navigate and screenshot",
        steps=[
            InteractionStep(step_type=StepType.NAVIGATE, target="http://localhost:3000"),
            InteractionStep(step_type=StepType.WAIT, timeout_ms=1000),
            InteractionStep(step_type=StepType.SCREENSHOT, description="homepage"),
        ],
    )


def test_interaction_result_defaults() -> None:
    result = InteractionResult()
    assert result.screenshots == []
    assert result.steps_completed == 0
    assert result.errors == []
    assert result.duration_seconds == 0.0


def test_interaction_result_with_data() -> None:
    result = InteractionResult(
        steps_completed=3,
        total_steps=5,
        screenshots=["/tmp/s1.png"],
        errors=["click failed"],
        duration_seconds=12.5,
    )
    assert result.steps_completed == 3
    assert len(result.screenshots) == 1
    assert len(result.errors) == 1


@pytest.mark.asyncio
async def test_execute_plan_returns_result(simple_plan: InteractionPlan) -> None:
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.screenshot = AsyncMock(return_value=b"fake-png")
    mock_page.title = AsyncMock(return_value="Test Page")

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    mock_chromium = MagicMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw_instance = MagicMock()
    mock_pw_instance.chromium = mock_chromium

    with patch("playwright.async_api.async_playwright") as mock_pw:
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_pw_instance)
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await execute_interaction_plan(simple_plan, output_dir="/tmp/test-interaction")

    assert isinstance(result, InteractionResult)
    assert result.total_steps == 3
    # Navigate + wait should succeed; screenshot may or may not depending on mock
    assert result.steps_completed >= 2


@pytest.mark.asyncio
async def test_execute_empty_plan() -> None:
    empty_plan = InteractionPlan(description="empty", steps=[])

    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_chromium = MagicMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)
    mock_pw_instance = MagicMock()
    mock_pw_instance.chromium = mock_chromium

    with patch("playwright.async_api.async_playwright") as mock_pw:
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_pw_instance)
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await execute_interaction_plan(empty_plan)

    assert result.steps_completed == 0
    assert result.total_steps == 0
    assert result.errors == []
