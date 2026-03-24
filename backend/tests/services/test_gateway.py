"""Tests for the gateway protocol."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.agent import InteractionPlan, StepType
from services.gateway import (
    DirectGateway,
    GatewayMessage,
    _parse_interaction_plan,
)


@pytest.fixture
def gateway() -> DirectGateway:
    return DirectGateway(api_key="test-key")


def test_gateway_message_creation() -> None:
    msg = GatewayMessage(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


def test_parse_interaction_plan_valid_json() -> None:
    raw = json.dumps(
        {
            "description": "Test login",
            "expected_outcome": "User sees dashboard",
            "steps": [
                {"step_type": "navigate", "target": "http://localhost:3000/login"},
                {"step_type": "type", "selector": "#email", "value": "test@test.com"},
                {"step_type": "click", "selector": "button[type=submit]"},
                {"step_type": "screenshot", "description": "after login"},
            ],
        }
    )
    plan = _parse_interaction_plan(raw)
    assert isinstance(plan, InteractionPlan)
    assert len(plan.steps) == 4
    assert plan.steps[0].step_type == StepType.NAVIGATE
    assert plan.steps[1].value == "test@test.com"
    assert plan.description == "Test login"


def test_parse_interaction_plan_empty_steps() -> None:
    raw = json.dumps({"description": "empty", "steps": []})
    plan = _parse_interaction_plan(raw)
    assert len(plan.steps) == 0


@pytest.mark.asyncio
async def test_direct_gateway_invoke_llm(gateway: DirectGateway) -> None:
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"steps": []}')]
    with patch("anthropic.AsyncAnthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client
        result = await gateway.invoke_llm([GatewayMessage(role="user", content="plan a demo")])
    assert isinstance(result, str)
    assert "steps" in result


@pytest.mark.asyncio
async def test_direct_gateway_generate_plan(gateway: DirectGateway) -> None:
    plan_json = json.dumps(
        {
            "description": "Test login",
            "expected_outcome": "User sees dashboard",
            "steps": [
                {"step_type": "navigate", "target": "http://localhost:3000/login"},
                {"step_type": "screenshot", "description": "after login"},
            ],
        }
    )
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=plan_json)]
    with patch("anthropic.AsyncAnthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client
        plan = await gateway.generate_interaction_plan(
            diff="+ added login button",
            app_url="http://localhost:3000",
        )
    assert isinstance(plan, InteractionPlan)
    assert len(plan.steps) == 2


@pytest.mark.asyncio
async def test_direct_gateway_upload_artifact(gateway: DirectGateway) -> None:
    result = await gateway.upload_artifact("/tmp/video.mp4", "video")
    assert result == "/tmp/video.mp4"


@pytest.mark.asyncio
async def test_direct_gateway_handles_markdown_wrapped_json(
    gateway: DirectGateway,
) -> None:
    wrapped = '```json\n{"description": "test", "steps": [{"step_type": "navigate", "target": "http://localhost"}]}\n```'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=wrapped)]
    with patch("anthropic.AsyncAnthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client
        plan = await gateway.generate_interaction_plan(diff="+ changes", app_url="http://localhost")
    assert len(plan.steps) == 1
