"""Gateway protocol — interface between agent and outside world.

Two implementations:
- DirectGateway: calls Claude API directly (local dev, evals)
- ControlPlaneGateway: proxies through control plane (production sandbox)

The agent code doesn't know which one it's using.
"""

import json
import logging
from dataclasses import dataclass
from typing import Protocol

from models.agent import InteractionPlan, InteractionStep, StepType

logger = logging.getLogger(__name__)

PLAN_SYSTEM_PROMPT = """You are an AI agent that demos software changes.
Given a git diff and an app URL, generate a browser interaction plan
to demonstrate what changed. Return ONLY valid JSON with this structure:
{
  "description": "what the demo shows",
  "expected_outcome": "what the reviewer should see",
  "steps": [
    {"step_type": "navigate", "target": "http://..."},
    {"step_type": "click", "selector": "button#id"},
    {"step_type": "type", "selector": "input#id", "value": "text"},
    {"step_type": "scroll", "target": "down"},
    {"step_type": "wait", "timeout_ms": 2000},
    {"step_type": "screenshot", "description": "after action"},
    {"step_type": "assert_text", "selector": ".result", "value": "expected text"},
    {"step_type": "assert_visible", "selector": ".element"}
  ]
}
Focus on demonstrating the actual changes in the diff. Be specific with selectors.
Always start with navigate and end with a screenshot."""


@dataclass
class GatewayMessage:
    """A message in the LLM conversation."""

    role: str  # "user" or "assistant"
    content: str


class Gateway(Protocol):
    """Protocol for agent-to-world communication."""

    async def invoke_llm(self, messages: list[GatewayMessage]) -> str: ...

    async def generate_interaction_plan(self, diff: str, app_url: str) -> InteractionPlan: ...

    async def upload_artifact(self, path: str, artifact_type: str) -> str: ...


def _parse_interaction_plan(raw_json: str) -> InteractionPlan:
    """Parse JSON into an InteractionPlan."""
    data = json.loads(raw_json)
    steps = []
    for s in data.get("steps", []):
        step_type = StepType(s["step_type"])
        steps.append(
            InteractionStep(
                step_type=step_type,
                target=s.get("target", ""),
                selector=s.get("selector", ""),
                value=s.get("value", ""),
                description=s.get("description", ""),
                timeout_ms=s.get("timeout_ms", 5000),
            )
        )
    return InteractionPlan(
        steps=steps,
        description=data.get("description", ""),
        expected_outcome=data.get("expected_outcome", ""),
    )


class DirectGateway:
    """Calls Claude API directly. For local dev and evals."""

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-20250514") -> None:
        self._api_key = api_key
        self._model = model

    async def invoke_llm(self, messages: list[GatewayMessage]) -> str:
        """Send messages to Claude and return the text response."""
        from anthropic import AsyncAnthropic
        from anthropic.types import MessageParam

        client = AsyncAnthropic(api_key=self._api_key)
        api_messages: list[MessageParam] = [
            {"role": m.role, "content": m.content}  # type: ignore[typeddict-item]
            for m in messages
        ]
        response = await client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=api_messages,
        )
        result = response.content[0].text  # type: ignore[union-attr]
        logger.info("LLM response received", extra={"length": len(result)})
        return result

    async def generate_interaction_plan(self, diff: str, app_url: str) -> InteractionPlan:
        """Ask Claude to generate a demo interaction plan from a diff."""
        user_msg = (
            f"App URL: {app_url}\n\nGit diff:\n```\n{diff}\n```\n\n"
            f"Generate an interaction plan to demo these changes."
        )
        messages = [
            GatewayMessage(role="user", content=PLAN_SYSTEM_PROMPT + "\n\n" + user_msg),
        ]
        raw = await self.invoke_llm(messages)
        # Extract JSON from response (may be wrapped in markdown code block)
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        plan = _parse_interaction_plan(raw.strip())
        logger.info(
            "Interaction plan generated",
            extra={"steps": len(plan.steps), "description": plan.description},
        )
        return plan

    async def upload_artifact(self, path: str, artifact_type: str) -> str:
        """In direct mode, artifacts stay local. Return the path as-is."""
        logger.info("Artifact stored locally", extra={"path": path, "type": artifact_type})
        return path


class ControlPlaneGateway:
    """Proxies all calls through the control plane. For production sandbox use."""

    def __init__(self, control_plane_url: str, session_token: str, session_id: str) -> None:
        self._base_url = control_plane_url.rstrip("/")
        self._token = session_token
        self._session_id = session_id

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    async def invoke_llm(self, messages: list[GatewayMessage]) -> str:
        """Proxy LLM call through the control plane."""
        import httpx

        payload = {
            "session_id": self._session_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/control/llm",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()["response"]

    async def generate_interaction_plan(self, diff: str, app_url: str) -> InteractionPlan:
        """Ask the control plane to generate an interaction plan."""
        user_msg = (
            f"App URL: {app_url}\n\nGit diff:\n```\n{diff}\n```\n\n"
            f"Generate an interaction plan to demo these changes."
        )
        messages = [
            GatewayMessage(role="user", content=PLAN_SYSTEM_PROMPT + "\n\n" + user_msg),
        ]
        raw = await self.invoke_llm(messages)
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        return _parse_interaction_plan(raw.strip())

    async def upload_artifact(self, path: str, artifact_type: str) -> str:
        """Upload an artifact to the control plane."""
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(path, "rb") as f:
                resp = await client.post(
                    f"{self._base_url}/api/control/artifacts",
                    files={"file": (path.split("/")[-1], f)},
                    data={
                        "session_id": self._session_id,
                        "artifact_type": artifact_type,
                    },
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()["url"]
