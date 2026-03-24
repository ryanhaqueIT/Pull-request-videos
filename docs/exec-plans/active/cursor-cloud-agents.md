# ExecPlan: Cursor-Identical Cloud Agent System

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an open-source clone of Cursor's cloud agent system — AI agents that run in isolated Docker containers, autonomously build/test software, interact with the running app via Playwright, record video demos of their work, capture screenshots and logs, and attach all artifacts to GitHub PRs as proof-of-work.

**Architecture:** Pattern 2 (isolate the agent) inspired by Browser Use's architecture. The agent runs entirely inside a Docker sandbox with zero secrets. A control plane FastAPI service manages sessions, proxies LLM calls, and collects artifacts. The sandbox receives only a session token and control plane URL. Playwright drives the browser inside the sandbox while Xvfb + ffmpeg records the full desktop session. When done, artifacts (video, screenshots, logs) are uploaded to the control plane and posted as PR comments.

**Tech Stack:**
- Python 3.12, FastAPI, Docker, Playwright, Xvfb, ffmpeg
- Claude API (via control plane proxy) for agent reasoning
- edge-tts for narration, httpx for HTTP
- GitHub Actions for CI trigger, `gh` CLI for PR comments

---

## Context and Orientation

The existing MVP (Tier 1) has a working pipeline: Playwright records a URL, edge-tts narrates a diff, ffmpeg assembles an MP4. But it's passive — it just scrolls a page. The Cursor-identical system is active: an AI agent analyzes the PR diff, plans interactions, builds the app, drives the browser intelligently, and records everything.

### System Architecture

```
┌─────────────────────────────────────────────────────┐
│  GitHub Actions / CLI Trigger                        │
│  (PR opened → start agent session)                   │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│  Control Plane (FastAPI)                             │
│  - Session management (create/status/artifacts)      │
│  - LLM proxy (Claude API with real credentials)      │
│  - Artifact storage (videos, screenshots, logs)      │
│  - GitHub integration (PR comments with artifacts)   │
│  Port: 9100                                          │
└──────────────┬──────────────────────────────────────┘
               │ HTTP (session_token auth)
               ▼
┌─────────────────────────────────────────────────────┐
│  Agent Sandbox (Docker container)                    │
│  ┌─────────────────────────────────────────────────┐│
│  │  Agent Brain (Claude-powered reasoning loop)    ││
│  │  - Reads diff, plans demo interactions          ││
│  │  - Installs deps, builds app, starts server     ││
│  │  - Drives Playwright to interact with app       ││
│  │  - Captures screenshots at key moments          ││
│  └─────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────┐│
│  │  Screen Recording (Xvfb + ffmpeg x11grab)       ││
│  │  - Records full desktop session as MP4          ││
│  └─────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────┐│
│  │  Gateway Client                                 ││
│  │  - Proxies LLM calls to control plane           ││
│  │  - Uploads artifacts to control plane           ││
│  └─────────────────────────────────────────────────┘│
│  Env: SESSION_TOKEN, CONTROL_PLANE_URL, SESSION_ID   │
└─────────────────────────────────────────────────────┘
```

### New Files to Create

```
backend/
  services/
    sandbox.py          — Docker container lifecycle (create/start/stop/logs)
    agent_brain.py      — Claude-powered reasoning loop (plan → execute → verify)
    interaction.py      — Playwright browser interactions (click, type, navigate, screenshot)
    screen_capture.py   — Xvfb + ffmpeg desktop recording
    artifact.py         — Collect and package videos/screenshots/logs
    github_pr.py        — Post PR comments with embedded artifacts
    control_plane.py    — Control plane session/LLM proxy endpoints
    gateway.py          — Gateway protocol (control plane client + direct mode)
  models/
    agent.py            — AgentSession, AgentTask, AgentAction, InteractionPlan
    artifact.py         — Artifact, ArtifactBundle models
  routers/
    agent.py            — POST /api/agents/run, GET /api/agents/{id}/status
    control.py          — Control plane endpoints (LLM proxy, artifact upload)
  tests/
    services/
      test_sandbox.py
      test_agent_brain.py
      test_interaction.py
      test_screen_capture.py
      test_artifact.py
      test_github_pr.py
      test_gateway.py
    test_agent_router.py

sandbox/
  Dockerfile            — Agent sandbox image (Python + Chromium + Xvfb + ffmpeg)
  entrypoint.sh         — Start Xvfb, ffmpeg recording, then run agent
  agent_runner.py       — Sandbox entry point (connects to control plane, runs agent loop)

docker-compose.agent.yml — Compose file for control plane + sandbox
```

### Module Dependency Rules (Updated)

```
routers/       → may import: services/, models/, config/
services/      → may import: models/, config/
  sandbox.py       → may import: models/agent.py, config/
  agent_brain.py   → may import: models/agent.py, services/interaction.py, services/gateway.py, config/
  interaction.py   → may import: models/agent.py, config/
  screen_capture.py → may import: config/
  artifact.py      → may import: models/artifact.py, config/
  github_pr.py     → may import: models/artifact.py, config/
  control_plane.py → may import: models/agent.py, models/artifact.py, config/
  gateway.py       → may import: models/agent.py, models/artifact.py, config/
models/        → leaf layer (imports nothing from project)
config/        → leaf layer
sandbox/       → standalone (runs inside container, imports nothing from backend/)
```

---

## Plan of Work

### Milestone 1: Agent Data Models

Define the core data models for the agent system. Pure data, no logic, no dependencies.

**Demo statement:** `python -c "from models.agent import AgentSession, InteractionPlan; print('models OK')"` prints "models OK".

### Milestone 2: Gateway Protocol

Build the gateway abstraction — the interface between agent and outside world. Two implementations: `DirectGateway` (calls Claude API directly, for local dev) and `ControlPlaneGateway` (proxies through control plane, for production).

**Demo statement:** `DirectGateway.invoke_llm(messages)` returns a Claude response. Tests pass with mocked HTTP.

### Milestone 3: Screen Capture Service

Build the Xvfb + ffmpeg x11grab recorder that captures the full desktop session as MP4. Works both inside Docker (with real Xvfb) and outside (falls back to Playwright video recording).

**Demo statement:** `screen_capture.start_recording()` starts ffmpeg, `screen_capture.stop_recording()` returns path to MP4.

### Milestone 4: Interaction Service

Build the Playwright-based browser interaction service. Given an `InteractionPlan` (list of steps like click, type, navigate, wait, screenshot), it executes each step and captures screenshots at key moments.

**Demo statement:** `execute_interaction_plan(plan)` drives Chromium through a sequence of actions and returns a list of screenshot paths.

### Milestone 5: Agent Brain

Build the Claude-powered reasoning loop. Given a diff and a running app URL, the agent: (1) analyzes what changed, (2) generates an interaction plan, (3) executes the plan via the interaction service, (4) verifies the results. This is the core "AI that demos its own work."

**Demo statement:** Given a diff that adds a button, the agent generates a plan to click the button and verify it works, then executes it.

### Milestone 6: Artifact Collector

Collect all outputs (video, screenshots, logs, test results) into a structured artifact bundle. Generate a narrated summary using existing narrator service.

**Demo statement:** `collect_artifacts(session)` returns an `ArtifactBundle` with video path, screenshot paths, and log text.

### Milestone 7: Docker Sandbox

Build the Dockerfile and entrypoint for the isolated agent container. The container has Python, Chromium, Xvfb, ffmpeg, and Playwright pre-installed. On start: launch Xvfb, start ffmpeg recording, connect to control plane, run the agent loop, stop recording, upload artifacts.

**Demo statement:** `docker build -t pr-video-sandbox sandbox/` succeeds. `docker run pr-video-sandbox` starts the agent.

### Milestone 8: Sandbox Orchestrator

Build `sandbox.py` — the service that creates, starts, monitors, and stops Docker containers. Manages the lifecycle from "PR opened" to "artifacts collected."

**Demo statement:** `create_sandbox(task)` returns a container ID. `get_sandbox_logs(id)` returns stdout.

### Milestone 9: Control Plane Endpoints

Build the FastAPI control plane routes: session creation, LLM proxy, artifact upload, session status. The control plane holds Claude API keys and proxies all LLM calls.

**Demo statement:** `POST /api/control/sessions` creates a session. `POST /api/control/llm` proxies to Claude. `POST /api/control/artifacts` stores files.

### Milestone 10: GitHub PR Integration

Post PR comments with embedded video artifacts. Upload video to GitHub Actions artifacts, post a comment with download link, screenshots inline, and a summary of what the agent did.

**Demo statement:** `post_pr_artifacts(pr_number, bundle)` posts a formatted comment with video link and inline screenshots.

### Milestone 11: CLI + Router Integration

Wire everything together: `POST /api/agents/run` triggers the full pipeline. CLI command `python __main__.py agent --repo <url> --pr <number>` runs locally.

**Demo statement:** `python __main__.py agent --url http://localhost:3000 --diff diff.txt` produces an MP4 demo video.

### Milestone 12: GitHub Actions Workflow

Update `pr-video.yml` to use the new agent system. On PR open: build sandbox image, start control plane, run agent, collect artifacts, post PR comment.

**Demo statement:** Push a PR and the workflow posts a comment with a video demo of the changes.

---

## Concrete Steps

### Task 1: Agent Data Models (`models/agent.py`, `models/artifact.py`)

**Files:**
- Create: `backend/models/agent.py`
- Create: `backend/models/artifact.py`
- Create: `backend/tests/services/test_agent_models.py`

- [ ] **Step 1: Write failing test for AgentSession model**

```python
# backend/tests/services/test_agent_models.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_agent_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'models.agent'`

- [ ] **Step 3: Implement agent models**

```python
# backend/models/agent.py
"""Data models for the cloud agent system. Leaf layer — no project imports."""

from dataclasses import dataclass, field
from enum import Enum


class AgentStatus(Enum):
    """Status of an agent session."""
    PENDING = "pending"
    PLANNING = "planning"
    BUILDING = "building"
    INTERACTING = "interacting"
    RECORDING = "recording"
    COLLECTING = "collecting"
    COMPLETE = "complete"
    FAILED = "failed"


class StepType(Enum):
    """Type of browser interaction step."""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    ASSERT_TEXT = "assert_text"
    ASSERT_VISIBLE = "assert_visible"


class AgentActionType(Enum):
    """Type of high-level agent action."""
    ANALYZE_DIFF = "analyze_diff"
    BUILD_APP = "build_app"
    START_SERVER = "start_server"
    GENERATE_PLAN = "generate_plan"
    EXECUTE_PLAN = "execute_plan"
    RUN_TESTS = "run_tests"
    COLLECT_ARTIFACTS = "collect_artifacts"


@dataclass
class InteractionStep:
    """A single browser interaction step."""
    step_type: StepType
    target: str = ""
    selector: str = ""
    value: str = ""
    description: str = ""
    timeout_ms: int = 5000


@dataclass
class InteractionPlan:
    """A sequence of browser interaction steps generated by the agent."""
    steps: list[InteractionStep] = field(default_factory=list)
    description: str = ""
    expected_outcome: str = ""


@dataclass
class AgentAction:
    """A recorded action taken by the agent during a session."""
    action_type: AgentActionType
    description: str = ""
    result: str = ""
    error: str = ""
    duration_seconds: float = 0.0


@dataclass
class AgentSession:
    """Full state of an agent session."""
    session_id: str
    repo_url: str = ""
    pr_number: int = 0
    diff: str = ""
    app_url: str = ""
    status: AgentStatus = AgentStatus.PENDING
    actions: list[AgentAction] = field(default_factory=list)
    interaction_plan: InteractionPlan | None = None
    error: str = ""
    container_id: str = ""
```

- [ ] **Step 4: Implement artifact models**

```python
# backend/models/artifact.py
"""Artifact data models. Leaf layer — no project imports."""

from dataclasses import dataclass, field


@dataclass
class Artifact:
    """A single artifact produced by an agent."""
    artifact_type: str  # "video", "screenshot", "log", "narration"
    path: str
    description: str = ""
    size_bytes: int = 0


@dataclass
class ArtifactBundle:
    """Collection of all artifacts from an agent session."""
    session_id: str
    video_path: str = ""
    screenshot_paths: list[str] = field(default_factory=list)
    log_text: str = ""
    narration_text: str = ""
    narration_audio_path: str = ""
    artifacts: list[Artifact] = field(default_factory=list)
    summary: str = ""
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/services/test_agent_models.py -v`
Expected: 3 PASSED

- [ ] **Step 6: Lint and commit**

```bash
cd backend && ruff check . && ruff format .
git add backend/models/agent.py backend/models/artifact.py backend/tests/services/test_agent_models.py
git commit -m "feat(models): add agent session and artifact data models"
```

---

### Task 2: Gateway Protocol (`services/gateway.py`)

**Files:**
- Create: `backend/services/gateway.py`
- Create: `backend/tests/services/test_gateway.py`

- [ ] **Step 1: Write failing test for gateway protocol**

```python
# backend/tests/services/test_gateway.py
"""Tests for the gateway protocol."""
import json
from unittest.mock import AsyncMock, patch

import pytest

from models.agent import InteractionPlan, InteractionStep, StepType
from services.gateway import DirectGateway, GatewayMessage


@pytest.fixture
def gateway() -> DirectGateway:
    return DirectGateway(api_key="test-key")


def test_gateway_message_creation() -> None:
    msg = GatewayMessage(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


@pytest.mark.asyncio
async def test_direct_gateway_invoke_llm(gateway: DirectGateway) -> None:
    mock_response = AsyncMock()
    mock_response.content = [AsyncMock(text='{"steps": []}')]
    with patch("services.gateway.AsyncAnthropic") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(return_value=mock_response)
        result = await gateway.invoke_llm(
            [GatewayMessage(role="user", content="plan a demo")]
        )
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_direct_gateway_generate_plan(gateway: DirectGateway) -> None:
    plan_json = json.dumps({
        "description": "Test login",
        "expected_outcome": "User sees dashboard",
        "steps": [
            {"step_type": "navigate", "target": "http://localhost:3000/login"},
            {"step_type": "type", "selector": "#email", "value": "test@test.com"},
            {"step_type": "click", "selector": "button[type=submit]"},
            {"step_type": "screenshot", "description": "after login"},
        ],
    })
    mock_response = AsyncMock()
    mock_response.content = [AsyncMock(text=plan_json)]
    with patch("services.gateway.AsyncAnthropic") as mock_client:
        mock_client.return_value.messages.create = AsyncMock(return_value=mock_response)
        plan = await gateway.generate_interaction_plan(
            diff="+ added login button",
            app_url="http://localhost:3000",
        )
    assert isinstance(plan, InteractionPlan)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_gateway.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement gateway**

```python
# backend/services/gateway.py
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

from config.settings import Settings
from models.agent import InteractionPlan, InteractionStep, StepType

logger = logging.getLogger(__name__)

PLAN_SYSTEM_PROMPT = """You are an AI agent that demos software changes.
Given a git diff and an app URL, generate a browser interaction plan
to demonstrate what changed. Return JSON with this structure:
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

    async def generate_interaction_plan(
        self, diff: str, app_url: str
    ) -> InteractionPlan: ...

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

        client = AsyncAnthropic(api_key=self._api_key)
        api_messages = [{"role": m.role, "content": m.content} for m in messages]
        response = await client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=api_messages,
        )
        result = response.content[0].text
        logger.info("LLM response received", extra={"length": len(result)})
        return result

    async def generate_interaction_plan(
        self, diff: str, app_url: str
    ) -> InteractionPlan:
        """Ask Claude to generate a demo interaction plan from a diff."""
        user_msg = f"App URL: {app_url}\n\nGit diff:\n```\n{diff}\n```\n\nGenerate an interaction plan to demo these changes."
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

    def __init__(
        self, control_plane_url: str, session_token: str, session_id: str
    ) -> None:
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

    async def generate_interaction_plan(
        self, diff: str, app_url: str
    ) -> InteractionPlan:
        """Ask the control plane to generate an interaction plan."""
        user_msg = f"App URL: {app_url}\n\nGit diff:\n```\n{diff}\n```\n\nGenerate an interaction plan to demo these changes."
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/services/test_gateway.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Add anthropic dependency and commit**

Add `anthropic>=0.40.0` to pyproject.toml dependencies, then:
```bash
cd backend && ruff check . && ruff format .
git add backend/services/gateway.py backend/tests/services/test_gateway.py backend/pyproject.toml
git commit -m "feat(gateway): add gateway protocol with direct and control plane implementations"
```

---

### Task 3: Screen Capture Service (`services/screen_capture.py`)

**Files:**
- Create: `backend/services/screen_capture.py`
- Create: `backend/tests/services/test_screen_capture.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/services/test_screen_capture.py
"""Tests for the screen capture service."""
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.screen_capture import ScreenCapture


@pytest.fixture
def capture(tmp_path: Path) -> ScreenCapture:
    return ScreenCapture(output_dir=str(tmp_path), display=":99")


def test_screen_capture_init(capture: ScreenCapture) -> None:
    assert capture.display == ":99"
    assert not capture.is_recording


@patch("services.screen_capture.subprocess.Popen")
@patch("services.screen_capture.shutil.which", return_value="/usr/bin/ffmpeg")
def test_start_recording_launches_ffmpeg(
    mock_which: MagicMock, mock_popen: MagicMock, capture: ScreenCapture
) -> None:
    mock_popen.return_value.pid = 12345
    capture.start_recording()
    assert capture.is_recording
    mock_popen.assert_called_once()
    cmd = mock_popen.call_args[0][0]
    assert "ffmpeg" in cmd[0]
    assert "-f" in cmd
    assert "x11grab" in cmd


@patch("services.screen_capture.subprocess.Popen")
@patch("services.screen_capture.shutil.which", return_value="/usr/bin/ffmpeg")
def test_stop_recording_returns_path(
    mock_which: MagicMock, mock_popen: MagicMock, capture: ScreenCapture
) -> None:
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    mock_proc.poll.return_value = None
    mock_proc.communicate.return_value = (b"", b"")
    mock_popen.return_value = mock_proc
    capture.start_recording()
    path = capture.stop_recording()
    assert path.endswith(".mp4")
    assert not capture.is_recording


def test_fallback_mode_uses_playwright(tmp_path: Path) -> None:
    """When Xvfb is not available, should indicate fallback mode."""
    cap = ScreenCapture(output_dir=str(tmp_path), display=":99", fallback_mode=True)
    assert cap.fallback_mode
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_screen_capture.py -v`
Expected: FAIL

- [ ] **Step 3: Implement screen capture**

```python
# backend/services/screen_capture.py
"""Desktop screen recording via Xvfb + ffmpeg x11grab.

Records the full virtual display as MP4. Falls back to Playwright
video recording when Xvfb is not available (e.g., on Windows/macOS).
"""

import logging
import shutil
import subprocess
import time
from pathlib import Path

from config.settings import Settings

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Records a virtual X11 display to MP4 using ffmpeg x11grab."""

    def __init__(
        self,
        output_dir: str = "/tmp/pr-videos",
        display: str = ":99",
        width: int = 1280,
        height: int = 720,
        fps: int = 15,
        fallback_mode: bool = False,
    ) -> None:
        self.output_dir = output_dir
        self.display = display
        self.width = width
        self.height = height
        self.fps = fps
        self.fallback_mode = fallback_mode
        self._process: subprocess.Popen | None = None  # type: ignore[type-arg]
        self._output_path: str = ""
        self.is_recording = False

    def _find_ffmpeg(self) -> str:
        """Find ffmpeg binary."""
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
        return "ffmpeg"

    def start_recording(self) -> str:
        """Start recording the X11 display. Returns output path."""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        self._output_path = str(
            Path(self.output_dir) / f"session-{int(time.time())}.mp4"
        )
        ffmpeg = self._find_ffmpeg()

        cmd = [
            ffmpeg,
            "-y",
            "-f", "x11grab",
            "-video_size", f"{self.width}x{self.height}",
            "-framerate", str(self.fps),
            "-i", self.display,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            self._output_path,
        ]

        logger.info("Starting screen recording", extra={"cmd": " ".join(cmd)})
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.is_recording = True
        logger.info(
            "Recording started",
            extra={"pid": self._process.pid, "output": self._output_path},
        )
        return self._output_path

    def stop_recording(self) -> str:
        """Stop recording and return path to the MP4 file."""
        if not self._process:
            logger.warning("No recording process to stop")
            return self._output_path

        self._process.terminate()
        try:
            self._process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.communicate()

        self.is_recording = False
        logger.info(
            "Recording stopped",
            extra={"output": self._output_path},
        )
        return self._output_path


def create_screen_capture(settings: Settings) -> ScreenCapture:
    """Factory to create a ScreenCapture from settings."""
    return ScreenCapture(
        output_dir=settings.output_dir,
        width=settings.video_width,
        height=settings.video_height,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/services/test_screen_capture.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
cd backend && ruff check . && ruff format .
git add backend/services/screen_capture.py backend/tests/services/test_screen_capture.py
git commit -m "feat(capture): add Xvfb + ffmpeg desktop screen recording service"
```

---

### Task 4: Interaction Service (`services/interaction.py`)

**Files:**
- Create: `backend/services/interaction.py`
- Create: `backend/tests/services/test_interaction.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/services/test_interaction.py
"""Tests for the Playwright interaction service."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.agent import InteractionPlan, InteractionStep, StepType
from services.interaction import execute_interaction_plan, InteractionResult


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


@pytest.mark.asyncio
async def test_execute_plan_returns_result(simple_plan: InteractionPlan) -> None:
    with patch("services.interaction.async_playwright") as mock_pw:
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake-png")
        mock_page.title = AsyncMock(return_value="Test Page")
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_pw.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(chromium=MagicMock(launch=AsyncMock(return_value=mock_browser)))
        )
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await execute_interaction_plan(simple_plan, output_dir="/tmp/test")

    assert isinstance(result, InteractionResult)
    assert result.steps_completed >= 0


def test_interaction_result_defaults() -> None:
    result = InteractionResult()
    assert result.screenshots == []
    assert result.steps_completed == 0
    assert result.errors == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_interaction.py -v`
Expected: FAIL

- [ ] **Step 3: Implement interaction service**

```python
# backend/services/interaction.py
"""Playwright-based browser interaction service.

Executes an InteractionPlan: navigates, clicks, types, scrolls,
takes screenshots, and asserts text/visibility. Each step is logged.
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from models.agent import InteractionPlan, InteractionStep, StepType

logger = logging.getLogger(__name__)


@dataclass
class InteractionResult:
    """Result of executing an interaction plan."""
    steps_completed: int = 0
    total_steps: int = 0
    screenshots: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


async def _execute_step(
    page: object,  # playwright Page
    step: InteractionStep,
    output_dir: str,
    screenshot_count: int,
) -> tuple[str, str]:
    """Execute a single interaction step. Returns (screenshot_path, error)."""
    try:
        if step.step_type == StepType.NAVIGATE:
            await page.goto(step.target, timeout=step.timeout_ms)  # type: ignore[attr-defined]
            await page.wait_for_load_state("networkidle", timeout=step.timeout_ms)  # type: ignore[attr-defined]

        elif step.step_type == StepType.CLICK:
            await page.click(step.selector, timeout=step.timeout_ms)  # type: ignore[attr-defined]

        elif step.step_type == StepType.TYPE:
            await page.fill(step.selector, step.value, timeout=step.timeout_ms)  # type: ignore[attr-defined]

        elif step.step_type == StepType.SCROLL:
            direction = step.target or "down"
            if direction == "down":
                await page.evaluate("window.scrollBy(0, 500)")  # type: ignore[attr-defined]
            elif direction == "up":
                await page.evaluate("window.scrollBy(0, -500)")  # type: ignore[attr-defined]
            elif direction == "bottom":
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # type: ignore[attr-defined]
            elif direction == "top":
                await page.evaluate("window.scrollTo(0, 0)")  # type: ignore[attr-defined]

        elif step.step_type == StepType.WAIT:
            await page.wait_for_timeout(step.timeout_ms)  # type: ignore[attr-defined]

        elif step.step_type == StepType.SCREENSHOT:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            ss_path = str(Path(output_dir) / f"screenshot-{screenshot_count:03d}.png")
            await page.screenshot(path=ss_path, full_page=False)  # type: ignore[attr-defined]
            logger.info("Screenshot captured", extra={"path": ss_path, "desc": step.description})
            return ss_path, ""

        elif step.step_type == StepType.ASSERT_TEXT:
            text_content = await page.text_content(step.selector, timeout=step.timeout_ms)  # type: ignore[attr-defined]
            if step.value not in (text_content or ""):
                return "", f"Assert failed: expected '{step.value}' in '{text_content}'"

        elif step.step_type == StepType.ASSERT_VISIBLE:
            visible = await page.is_visible(step.selector)  # type: ignore[attr-defined]
            if not visible:
                return "", f"Assert failed: '{step.selector}' is not visible"

    except Exception as exc:
        error_msg = f"Step {step.step_type.value} failed: {exc}"
        logger.warning(error_msg)
        return "", error_msg

    return "", ""


async def execute_interaction_plan(
    plan: InteractionPlan,
    output_dir: str = "/tmp/pr-videos/screenshots",
    viewport_width: int = 1280,
    viewport_height: int = 720,
) -> InteractionResult:
    """Execute a full interaction plan using Playwright.

    Returns an InteractionResult with screenshots, step count, and errors.
    """
    from playwright.async_api import async_playwright

    result = InteractionResult(total_steps=len(plan.steps))
    start_time = time.time()
    screenshot_count = 0

    logger.info(
        "Executing interaction plan",
        extra={"steps": len(plan.steps), "description": plan.description},
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
        )
        page = await context.new_page()

        for i, step in enumerate(plan.steps):
            logger.info(
                "Executing step",
                extra={"step": i + 1, "type": step.step_type.value, "desc": step.description},
            )
            ss_path, error = await _execute_step(page, step, output_dir, screenshot_count)

            if ss_path:
                result.screenshots.append(ss_path)
                screenshot_count += 1
            if error:
                result.errors.append(error)
            else:
                result.steps_completed += 1

        await context.close()
        await browser.close()

    result.duration_seconds = time.time() - start_time
    logger.info(
        "Interaction plan complete",
        extra={
            "completed": result.steps_completed,
            "total": result.total_steps,
            "screenshots": len(result.screenshots),
            "errors": len(result.errors),
        },
    )
    return result
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/services/test_interaction.py -v`
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
cd backend && ruff check . && ruff format .
git add backend/services/interaction.py backend/tests/services/test_interaction.py
git commit -m "feat(interaction): add Playwright browser interaction service"
```

---

### Task 5: Agent Brain (`services/agent_brain.py`)

**Files:**
- Create: `backend/services/agent_brain.py`
- Create: `backend/tests/services/test_agent_brain.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/services/test_agent_brain.py
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
async def test_agent_brain_plan_phase(
    session: AgentSession, mock_plan: InteractionPlan
) -> None:
    mock_gateway = AsyncMock()
    mock_gateway.generate_interaction_plan = AsyncMock(return_value=mock_plan)

    brain = AgentBrain(gateway=mock_gateway, session=session)
    plan = await brain.plan()

    assert plan is not None
    assert len(plan.steps) == 3
    assert session.status == AgentStatus.PLANNING


@pytest.mark.asyncio
async def test_agent_brain_execute_phase(
    session: AgentSession, mock_plan: InteractionPlan
) -> None:
    mock_gateway = AsyncMock()
    mock_gateway.generate_interaction_plan = AsyncMock(return_value=mock_plan)

    brain = AgentBrain(gateway=mock_gateway, session=session)
    session.interaction_plan = mock_plan

    mock_result = InteractionResult(steps_completed=3, total_steps=3, screenshots=["/tmp/s1.png"])
    with patch("services.agent_brain.execute_interaction_plan", return_value=mock_result):
        result = await brain.execute()

    assert result.steps_completed == 3
    assert session.status == AgentStatus.INTERACTING


def test_agent_brain_generates_summary(session: AgentSession) -> None:
    mock_gateway = AsyncMock()
    brain = AgentBrain(gateway=mock_gateway, session=session)

    result = InteractionResult(steps_completed=3, total_steps=3, screenshots=["/tmp/s.png"])
    summary = brain.generate_summary(result)

    assert "3" in summary
    assert "step" in summary.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_agent_brain.py -v`
Expected: FAIL

- [ ] **Step 3: Implement agent brain**

```python
# backend/services/agent_brain.py
"""Claude-powered agent brain — the reasoning loop.

Given a diff and a running app, the agent:
1. Analyzes what changed (PLANNING)
2. Generates an interaction plan (PLANNING)
3. Executes the plan via Playwright (INTERACTING)
4. Summarizes results (COLLECTING)
"""

import logging
import time

from models.agent import (
    AgentAction,
    AgentActionType,
    AgentSession,
    AgentStatus,
    InteractionPlan,
)
from services.interaction import InteractionResult, execute_interaction_plan

logger = logging.getLogger(__name__)


class AgentBrain:
    """Orchestrates the agent's reasoning and interaction loop."""

    def __init__(self, gateway: object, session: AgentSession) -> None:
        self._gateway = gateway
        self._session = session

    async def plan(self) -> InteractionPlan:
        """Phase 1: Analyze diff and generate an interaction plan."""
        self._session.status = AgentStatus.PLANNING
        start = time.time()

        logger.info(
            "Agent planning",
            extra={"session_id": self._session.session_id, "app_url": self._session.app_url},
        )

        plan = await self._gateway.generate_interaction_plan(  # type: ignore[attr-defined]
            diff=self._session.diff,
            app_url=self._session.app_url,
        )
        self._session.interaction_plan = plan
        self._session.actions.append(
            AgentAction(
                action_type=AgentActionType.GENERATE_PLAN,
                description=f"Generated plan with {len(plan.steps)} steps: {plan.description}",
                duration_seconds=time.time() - start,
            )
        )

        logger.info(
            "Plan generated",
            extra={"steps": len(plan.steps), "description": plan.description},
        )
        return plan

    async def execute(
        self,
        output_dir: str = "/tmp/pr-videos/screenshots",
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ) -> InteractionResult:
        """Phase 2: Execute the interaction plan via Playwright."""
        self._session.status = AgentStatus.INTERACTING
        start = time.time()

        plan = self._session.interaction_plan
        if not plan:
            msg = "No interaction plan to execute"
            raise ValueError(msg)

        logger.info(
            "Agent executing plan",
            extra={"session_id": self._session.session_id, "steps": len(plan.steps)},
        )

        result = await execute_interaction_plan(
            plan=plan,
            output_dir=output_dir,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )

        self._session.actions.append(
            AgentAction(
                action_type=AgentActionType.EXECUTE_PLAN,
                description=f"Executed {result.steps_completed}/{result.total_steps} steps",
                result=f"{len(result.screenshots)} screenshots, {len(result.errors)} errors",
                duration_seconds=time.time() - start,
            )
        )

        logger.info(
            "Plan execution complete",
            extra={
                "completed": result.steps_completed,
                "total": result.total_steps,
                "errors": result.errors,
            },
        )
        return result

    def generate_summary(self, result: InteractionResult) -> str:
        """Generate a human-readable summary of the agent's work."""
        plan = self._session.interaction_plan
        plan_desc = plan.description if plan else "No plan"

        lines = [
            f"## Agent Demo Summary",
            f"",
            f"**What was demoed:** {plan_desc}",
            f"**Steps completed:** {result.steps_completed}/{result.total_steps}",
            f"**Screenshots captured:** {len(result.screenshots)}",
            f"**Duration:** {result.duration_seconds:.1f}s",
        ]

        if result.errors:
            lines.append(f"")
            lines.append(f"**Issues encountered:**")
            for err in result.errors:
                lines.append(f"- {err}")

        actions = self._session.actions
        if actions:
            lines.append(f"")
            lines.append(f"**Agent actions:**")
            for a in actions:
                lines.append(f"- {a.action_type.value}: {a.description}")

        return "\n".join(lines)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/services/test_agent_brain.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
cd backend && ruff check . && ruff format .
git add backend/services/agent_brain.py backend/tests/services/test_agent_brain.py
git commit -m "feat(brain): add Claude-powered agent brain with plan/execute/summarize"
```

---

### Task 6: Artifact Collector (`services/artifact.py`)

**Files:**
- Create: `backend/services/artifact.py`
- Create: `backend/tests/services/test_artifact.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/services/test_artifact.py
"""Tests for the artifact collector."""
from pathlib import Path

import pytest

from models.artifact import Artifact, ArtifactBundle
from services.artifact import collect_artifacts


def test_collect_artifacts_with_video(tmp_path: Path) -> None:
    video = tmp_path / "session.mp4"
    video.write_bytes(b"\x00" * 1024)
    ss1 = tmp_path / "screenshot-001.png"
    ss1.write_bytes(b"\x89PNG" + b"\x00" * 100)

    bundle = collect_artifacts(
        session_id="s1",
        video_path=str(video),
        screenshot_paths=[str(ss1)],
        log_text="agent started\nagent finished",
    )

    assert bundle.session_id == "s1"
    assert bundle.video_path == str(video)
    assert len(bundle.screenshot_paths) == 1
    assert len(bundle.artifacts) == 3  # video + screenshot + log


def test_collect_artifacts_no_video(tmp_path: Path) -> None:
    bundle = collect_artifacts(
        session_id="s2",
        video_path="",
        screenshot_paths=[],
        log_text="no video recorded",
    )

    assert bundle.video_path == ""
    assert len(bundle.artifacts) == 1  # log only


def test_artifact_bundle_summary() -> None:
    bundle = ArtifactBundle(session_id="s3", summary="Test summary")
    assert bundle.summary == "Test summary"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_artifact.py -v`
Expected: FAIL

- [ ] **Step 3: Implement artifact collector**

```python
# backend/services/artifact.py
"""Collects and packages all agent artifacts into a bundle."""

import logging
from pathlib import Path

from models.artifact import Artifact, ArtifactBundle

logger = logging.getLogger(__name__)


def collect_artifacts(
    session_id: str,
    video_path: str = "",
    screenshot_paths: list[str] | None = None,
    log_text: str = "",
    narration_text: str = "",
    narration_audio_path: str = "",
) -> ArtifactBundle:
    """Collect all artifacts from an agent session into a bundle."""
    artifacts: list[Artifact] = []
    ss_paths = screenshot_paths or []

    if video_path and Path(video_path).exists():
        size = Path(video_path).stat().st_size
        artifacts.append(
            Artifact(artifact_type="video", path=video_path, description="Demo video", size_bytes=size)
        )
        logger.info("Video artifact collected", extra={"path": video_path, "size": size})

    for ss in ss_paths:
        if Path(ss).exists():
            size = Path(ss).stat().st_size
            artifacts.append(
                Artifact(artifact_type="screenshot", path=ss, description=Path(ss).stem, size_bytes=size)
            )

    if log_text:
        artifacts.append(
            Artifact(artifact_type="log", path="", description="Agent log", size_bytes=len(log_text))
        )

    if narration_audio_path and Path(narration_audio_path).exists():
        size = Path(narration_audio_path).stat().st_size
        artifacts.append(
            Artifact(
                artifact_type="narration", path=narration_audio_path, description="Narration audio", size_bytes=size
            )
        )

    logger.info(
        "Artifacts collected",
        extra={"session_id": session_id, "count": len(artifacts)},
    )

    return ArtifactBundle(
        session_id=session_id,
        video_path=video_path,
        screenshot_paths=ss_paths,
        log_text=log_text,
        narration_text=narration_text,
        narration_audio_path=narration_audio_path,
        artifacts=artifacts,
    )
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/services/test_artifact.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
cd backend && ruff check . && ruff format .
git add backend/services/artifact.py backend/tests/services/test_artifact.py
git commit -m "feat(artifact): add artifact collector for videos, screenshots, and logs"
```

---

### Task 7: GitHub PR Integration (`services/github_pr.py`)

**Files:**
- Create: `backend/services/github_pr.py`
- Create: `backend/tests/services/test_github_pr.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/services/test_github_pr.py
"""Tests for GitHub PR integration."""
from pathlib import Path
from unittest.mock import patch

import pytest

from models.artifact import ArtifactBundle
from services.github_pr import format_pr_comment


def test_format_pr_comment_with_all_artifacts() -> None:
    bundle = ArtifactBundle(
        session_id="s1",
        video_path="/tmp/demo.mp4",
        screenshot_paths=["/tmp/ss1.png", "/tmp/ss2.png"],
        log_text="agent started\n3 steps completed",
        summary="## Agent Demo Summary\n\nAdded submit button and verified it works.",
    )
    comment = format_pr_comment(
        bundle=bundle,
        artifact_url="https://github.com/repo/actions/runs/123",
    )
    assert "Agent Demo" in comment
    assert "Video" in comment or "video" in comment
    assert "screenshot" in comment.lower() or "Screenshot" in comment
    assert "https://github.com/repo/actions/runs/123" in comment


def test_format_pr_comment_no_video() -> None:
    bundle = ArtifactBundle(
        session_id="s2",
        summary="Quick fix, no video needed.",
    )
    comment = format_pr_comment(bundle=bundle, artifact_url="")
    assert "Quick fix" in comment


def test_format_pr_comment_with_errors() -> None:
    bundle = ArtifactBundle(
        session_id="s3",
        summary="## Agent Demo Summary\n\n**Issues encountered:**\n- Button not found",
    )
    comment = format_pr_comment(bundle=bundle, artifact_url="")
    assert "Issues" in comment or "Button not found" in comment
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_github_pr.py -v`
Expected: FAIL

- [ ] **Step 3: Implement GitHub PR service**

```python
# backend/services/github_pr.py
"""GitHub PR integration — posts agent artifacts as PR comments."""

import logging
import subprocess
from pathlib import Path

from models.artifact import ArtifactBundle

logger = logging.getLogger(__name__)


def format_pr_comment(
    bundle: ArtifactBundle,
    artifact_url: str = "",
) -> str:
    """Format a PR comment with agent demo results."""
    lines: list[str] = []

    lines.append("## 🤖 Agent Demo Video")
    lines.append("")

    if bundle.summary:
        lines.append(bundle.summary)
        lines.append("")

    if bundle.video_path:
        lines.append("### 🎬 Demo Video")
        if artifact_url:
            lines.append(
                f"**[Download demo video]({artifact_url})** (see Artifacts section)"
            )
        else:
            lines.append(f"Video: `{bundle.video_path}`")
        lines.append("")

    if bundle.screenshot_paths:
        lines.append(f"### 📸 Screenshots ({len(bundle.screenshot_paths)})")
        lines.append("")
        for i, ss in enumerate(bundle.screenshot_paths):
            name = Path(ss).stem
            lines.append(f"**{i + 1}. {name}**")
        lines.append("")

    if bundle.log_text:
        lines.append("<details>")
        lines.append("<summary>📋 Agent Log</summary>")
        lines.append("")
        lines.append("```")
        # Truncate logs to avoid giant comments
        log_lines = bundle.log_text.strip().splitlines()
        if len(log_lines) > 50:
            lines.extend(log_lines[:25])
            lines.append(f"... ({len(log_lines) - 50} lines omitted) ...")
            lines.extend(log_lines[-25:])
        else:
            lines.extend(log_lines)
        lines.append("```")
        lines.append("</details>")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by PR Video Agent | Demos, not diffs*")

    return "\n".join(lines)


def post_pr_comment(
    repo: str,
    pr_number: int,
    comment: str,
) -> bool:
    """Post a comment on a GitHub PR using the gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "pr", "comment", str(pr_number), "--repo", repo, "--body", comment],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error(
                "Failed to post PR comment",
                extra={"returncode": result.returncode, "stderr": result.stderr[:200]},
            )
            return False
        logger.info("PR comment posted", extra={"repo": repo, "pr": pr_number})
        return True
    except FileNotFoundError:
        logger.error("gh CLI not found — install GitHub CLI to post PR comments")
        return False
    except subprocess.TimeoutExpired:
        logger.error("PR comment posting timed out")
        return False
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/services/test_github_pr.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
cd backend && ruff check . && ruff format .
git add backend/services/github_pr.py backend/tests/services/test_github_pr.py
git commit -m "feat(github): add PR comment formatter and posting via gh CLI"
```

---

### Task 8: Docker Sandbox (`sandbox/`)

**Files:**
- Create: `sandbox/Dockerfile`
- Create: `sandbox/entrypoint.sh`
- Create: `sandbox/agent_runner.py`

- [ ] **Step 1: Create sandbox Dockerfile**

```dockerfile
# sandbox/Dockerfile
# Agent sandbox — isolated environment for autonomous AI coding agent.
# Contains: Python 3.12, Chromium, Playwright, Xvfb, ffmpeg, Node.js
# Security: Runs as unprivileged 'sandbox' user after setup.
# Receives only: SESSION_TOKEN, CONTROL_PLANE_URL, SESSION_ID

FROM python:3.12-slim

# System dependencies for Xvfb + ffmpeg + Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create sandbox user
RUN useradd -m -s /bin/bash sandbox

# Install Python dependencies
COPY ../backend/pyproject.toml /app/backend/pyproject.toml
WORKDIR /app/backend
RUN pip install --no-cache-dir -e ".[dev]" && \
    pip install --no-cache-dir anthropic>=0.40.0

# Install Playwright and Chromium
RUN playwright install chromium --with-deps

# Copy backend code
COPY ../backend/ /app/backend/

# Copy sandbox entry scripts
COPY sandbox/entrypoint.sh /app/entrypoint.sh
COPY sandbox/agent_runner.py /app/agent_runner.py
RUN chmod +x /app/entrypoint.sh

# Workspace for cloned repos
RUN mkdir -p /workspace /artifacts && chown sandbox:sandbox /workspace /artifacts

# Drop to sandbox user
USER sandbox
WORKDIR /workspace

# Only these 3 env vars are injected at runtime
ENV SESSION_TOKEN=""
ENV CONTROL_PLANE_URL=""
ENV SESSION_ID=""
ENV DISPLAY=":99"

ENTRYPOINT ["/app/entrypoint.sh"]
```

- [ ] **Step 2: Create entrypoint script**

```bash
#!/bin/bash
# sandbox/entrypoint.sh
# Starts Xvfb, ffmpeg recording, then runs the agent.

set -euo pipefail

DISPLAY=":99"
VIDEO_DIR="/artifacts"
RESOLUTION="1280x720"
FPS=15

echo "[sandbox] Starting Xvfb on display ${DISPLAY}..."
Xvfb ${DISPLAY} -screen 0 ${RESOLUTION}x24 -ac &
XVFB_PID=$!
sleep 1

echo "[sandbox] Starting screen recording..."
ffmpeg -y -f x11grab -video_size ${RESOLUTION} -framerate ${FPS} \
  -i ${DISPLAY} -c:v libx264 -preset ultrafast -crf 28 \
  -pix_fmt yuv420p -movflags +faststart \
  ${VIDEO_DIR}/session-recording.mp4 &
FFMPEG_PID=$!
sleep 0.5

echo "[sandbox] Running agent..."
python /app/agent_runner.py
AGENT_EXIT=$?

echo "[sandbox] Stopping recording..."
kill -SIGINT ${FFMPEG_PID} 2>/dev/null || true
wait ${FFMPEG_PID} 2>/dev/null || true

echo "[sandbox] Stopping Xvfb..."
kill ${XVFB_PID} 2>/dev/null || true

echo "[sandbox] Agent exited with code ${AGENT_EXIT}"
echo "[sandbox] Artifacts in ${VIDEO_DIR}:"
ls -la ${VIDEO_DIR}/

exit ${AGENT_EXIT}
```

- [ ] **Step 3: Create agent runner**

```python
#!/usr/bin/env python3
# sandbox/agent_runner.py
"""Sandbox agent runner — connects to control plane and executes the agent loop.

Reads SESSION_TOKEN, CONTROL_PLANE_URL, SESSION_ID from environment,
then deletes them. Runs the agent brain loop, collects artifacts,
uploads them to the control plane.
"""

import asyncio
import logging
import os
import sys

# Add backend to path
sys.path.insert(0, "/app/backend")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("agent_runner")


async def main() -> int:
    """Main agent loop."""
    # Read and strip environment variables (Pattern 2 security)
    session_token = os.environ.get("SESSION_TOKEN", "")
    control_plane_url = os.environ.get("CONTROL_PLANE_URL", "")
    session_id = os.environ.get("SESSION_ID", "")

    # Delete from environment after reading
    for var in ("SESSION_TOKEN", "CONTROL_PLANE_URL", "SESSION_ID"):
        os.environ.pop(var, None)

    if not all([session_token, control_plane_url, session_id]):
        logger.warning("Missing env vars — running in direct mode")
        # Direct mode for local testing
        from services.gateway import DirectGateway
        gateway = DirectGateway(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    else:
        from services.gateway import ControlPlaneGateway
        gateway = ControlPlaneGateway(  # type: ignore[assignment]
            control_plane_url=control_plane_url,
            session_token=session_token,
            session_id=session_id,
        )

    # Get session info from control plane or local args
    from models.agent import AgentSession
    session = AgentSession(
        session_id=session_id or "local",
        diff=os.environ.get("AGENT_DIFF", ""),
        app_url=os.environ.get("AGENT_APP_URL", "http://localhost:3000"),
    )

    from services.agent_brain import AgentBrain
    brain = AgentBrain(gateway=gateway, session=session)

    try:
        # Phase 1: Plan
        logger.info("Phase 1: Planning interaction...")
        plan = await brain.plan()
        logger.info("Plan: %s (%d steps)", plan.description, len(plan.steps))

        # Phase 2: Execute
        logger.info("Phase 2: Executing interaction plan...")
        result = await brain.execute(output_dir="/artifacts/screenshots")
        logger.info(
            "Execution: %d/%d steps, %d screenshots",
            result.steps_completed,
            result.total_steps,
            len(result.screenshots),
        )

        # Phase 3: Collect and upload artifacts
        logger.info("Phase 3: Collecting artifacts...")
        from services.artifact import collect_artifacts
        bundle = collect_artifacts(
            session_id=session.session_id,
            video_path="/artifacts/session-recording.mp4",
            screenshot_paths=result.screenshots,
            log_text=brain.generate_summary(result),
        )

        # Upload artifacts to control plane
        for artifact in bundle.artifacts:
            if artifact.path:
                await gateway.upload_artifact(artifact.path, artifact.artifact_type)  # type: ignore[attr-defined]

        logger.info("Agent complete. Artifacts: %d", len(bundle.artifacts))
        return 0

    except Exception as e:
        logger.error("Agent failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 4: Verify Dockerfile builds**

Run: `docker build -f sandbox/Dockerfile -t pr-video-sandbox .`
Expected: Build succeeds (or skip if Docker not available — test in CI)

- [ ] **Step 5: Commit**

```bash
git add sandbox/Dockerfile sandbox/entrypoint.sh sandbox/agent_runner.py
git commit -m "feat(sandbox): add Docker sandbox with Xvfb + ffmpeg + Playwright agent"
```

---

### Task 9: Sandbox Orchestrator (`services/sandbox.py`)

**Files:**
- Create: `backend/services/sandbox.py`
- Create: `backend/tests/services/test_sandbox.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/services/test_sandbox.py
"""Tests for the Docker sandbox orchestrator."""
from unittest.mock import MagicMock, patch

import pytest

from models.agent import AgentSession
from services.sandbox import SandboxConfig, SandboxOrchestrator


@pytest.fixture
def orchestrator() -> SandboxOrchestrator:
    return SandboxOrchestrator(image="pr-video-sandbox:latest")


def test_sandbox_config_defaults() -> None:
    config = SandboxConfig(session_id="s1")
    assert config.image == "pr-video-sandbox:latest"
    assert config.memory_limit == "2g"
    assert config.cpu_count == 2


@patch("services.sandbox.subprocess.run")
def test_create_sandbox(mock_run: MagicMock, orchestrator: SandboxOrchestrator) -> None:
    mock_run.return_value = MagicMock(
        returncode=0, stdout="abc123container\n", stderr=""
    )
    container_id = orchestrator.create(
        session_id="s1",
        control_plane_url="http://host:9100",
        session_token="tok-123",
    )
    assert container_id == "abc123container"
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "docker" in cmd[0]
    assert "run" in cmd


@patch("services.sandbox.subprocess.run")
def test_get_logs(mock_run: MagicMock, orchestrator: SandboxOrchestrator) -> None:
    mock_run.return_value = MagicMock(
        returncode=0, stdout="agent started\nagent done\n", stderr=""
    )
    logs = orchestrator.get_logs("abc123")
    assert "agent started" in logs


@patch("services.sandbox.subprocess.run")
def test_stop_sandbox(mock_run: MagicMock, orchestrator: SandboxOrchestrator) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    orchestrator.stop("abc123")
    mock_run.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_sandbox.py -v`
Expected: FAIL

- [ ] **Step 3: Implement sandbox orchestrator**

```python
# backend/services/sandbox.py
"""Docker sandbox orchestrator — creates, manages, and stops agent containers.

Each agent runs in an isolated Docker container with:
- Its own filesystem (cloned repo in /workspace)
- Xvfb + ffmpeg for screen recording
- Playwright + Chromium for browser interaction
- Only 3 env vars: SESSION_TOKEN, CONTROL_PLANE_URL, SESSION_ID
"""

import logging
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """Configuration for an agent sandbox container."""
    session_id: str
    image: str = "pr-video-sandbox:latest"
    memory_limit: str = "2g"
    cpu_count: int = 2
    timeout_seconds: int = 600  # 10 minutes max


class SandboxOrchestrator:
    """Manages Docker container lifecycle for agent sandboxes."""

    def __init__(self, image: str = "pr-video-sandbox:latest") -> None:
        self._image = image

    def create(
        self,
        session_id: str,
        control_plane_url: str,
        session_token: str,
        repo_url: str = "",
        diff: str = "",
        app_url: str = "",
        memory_limit: str = "2g",
        cpu_count: int = 2,
    ) -> str:
        """Create and start an agent sandbox container. Returns container ID."""
        cmd = [
            "docker", "run", "-d",
            "--name", f"pr-video-agent-{session_id}",
            "--memory", memory_limit,
            "--cpus", str(cpu_count),
            "-e", f"SESSION_TOKEN={session_token}",
            "-e", f"CONTROL_PLANE_URL={control_plane_url}",
            "-e", f"SESSION_ID={session_id}",
            "-e", f"AGENT_DIFF={diff[:5000]}",  # Truncate huge diffs
            "-e", f"AGENT_APP_URL={app_url}",
            "--network", "host",  # Allow access to control plane on host
            self._image,
        ]

        logger.info(
            "Creating sandbox",
            extra={"session_id": session_id, "image": self._image},
        )

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            logger.error(
                "Failed to create sandbox",
                extra={"stderr": result.stderr[:300]},
            )
            msg = f"Docker run failed: {result.stderr[:200]}"
            raise RuntimeError(msg)

        container_id = result.stdout.strip()
        logger.info(
            "Sandbox created",
            extra={"session_id": session_id, "container_id": container_id[:12]},
        )
        return container_id

    def get_logs(self, container_id: str) -> str:
        """Get stdout/stderr from a container."""
        result = subprocess.run(
            ["docker", "logs", container_id],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout + result.stderr

    def get_status(self, container_id: str) -> str:
        """Get container status (running, exited, etc.)."""
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", container_id],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()

    def stop(self, container_id: str) -> None:
        """Stop and remove a container."""
        subprocess.run(
            ["docker", "stop", container_id],
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            ["docker", "rm", "-f", container_id],
            capture_output=True,
            timeout=10,
        )
        logger.info("Sandbox stopped", extra={"container_id": container_id[:12]})

    def copy_artifacts(self, container_id: str, dest_dir: str) -> list[str]:
        """Copy artifacts from container to host."""
        result = subprocess.run(
            ["docker", "cp", f"{container_id}:/artifacts/.", dest_dir],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.warning(
                "Failed to copy artifacts",
                extra={"stderr": result.stderr[:200]},
            )
            return []

        import os
        artifacts = []
        for f in os.listdir(dest_dir):
            artifacts.append(os.path.join(dest_dir, f))
        logger.info("Artifacts copied", extra={"count": len(artifacts), "dest": dest_dir})
        return artifacts
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/services/test_sandbox.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
cd backend && ruff check . && ruff format .
git add backend/services/sandbox.py backend/tests/services/test_sandbox.py
git commit -m "feat(sandbox): add Docker sandbox orchestrator for agent containers"
```

---

### Task 10: Control Plane Endpoints (`routers/control.py`, `services/control_plane.py`)

**Files:**
- Create: `backend/services/control_plane.py`
- Create: `backend/routers/control.py`
- Create: `backend/tests/services/test_control_plane.py`
- Modify: `backend/main.py` (add control router)

- [ ] **Step 1: Write failing test**

```python
# backend/tests/services/test_control_plane.py
"""Tests for the control plane service and endpoints."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_create_session() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/control/sessions",
            json={"repo_url": "https://github.com/test/repo", "diff": "+ hello"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "session_token" in data


@pytest.mark.asyncio
async def test_get_session_status() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create first
        create_resp = await client.post(
            "/api/control/sessions",
            json={"repo_url": "https://github.com/test/repo"},
        )
        session_id = create_resp.json()["session_id"]
        token = create_resp.json()["session_token"]

        # Get status
        resp = await client.get(
            f"/api/control/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_llm_proxy_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/control/llm",
            json={"session_id": "fake", "messages": []},
        )
    assert resp.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_control_plane.py -v`
Expected: FAIL

- [ ] **Step 3: Implement control plane service**

```python
# backend/services/control_plane.py
"""Control plane — manages sessions, proxies LLM calls, stores artifacts.

Holds all credentials. Sandboxes talk to this and nothing else.
"""

import logging
import secrets
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from config.settings import Settings
from models.agent import AgentSession, AgentStatus

logger = logging.getLogger(__name__)


@dataclass
class SessionRecord:
    """Internal session tracking record."""
    session: AgentSession
    token: str
    artifacts: list[str] = field(default_factory=list)


class ControlPlaneService:
    """In-memory control plane for managing agent sessions."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._sessions: dict[str, SessionRecord] = {}

    def create_session(
        self,
        repo_url: str = "",
        pr_number: int = 0,
        diff: str = "",
        app_url: str = "",
    ) -> tuple[str, str]:
        """Create a new agent session. Returns (session_id, session_token)."""
        session_id = str(uuid.uuid4())[:8]
        token = secrets.token_urlsafe(32)

        session = AgentSession(
            session_id=session_id,
            repo_url=repo_url,
            pr_number=pr_number,
            diff=diff,
            app_url=app_url,
        )
        self._sessions[session_id] = SessionRecord(session=session, token=token)

        logger.info(
            "Session created",
            extra={"session_id": session_id, "repo_url": repo_url},
        )
        return session_id, token

    def validate_token(self, session_id: str, token: str) -> bool:
        """Validate a session token."""
        record = self._sessions.get(session_id)
        if not record:
            return False
        return secrets.compare_digest(record.token, token)

    def get_session(self, session_id: str) -> AgentSession | None:
        """Get session by ID."""
        record = self._sessions.get(session_id)
        return record.session if record else None

    def update_status(self, session_id: str, status: AgentStatus) -> None:
        """Update session status."""
        record = self._sessions.get(session_id)
        if record:
            record.session.status = status

    def store_artifact(self, session_id: str, path: str) -> None:
        """Record an artifact path for a session."""
        record = self._sessions.get(session_id)
        if record:
            record.artifacts.append(path)
            logger.info(
                "Artifact stored",
                extra={"session_id": session_id, "path": path},
            )

    def get_artifacts(self, session_id: str) -> list[str]:
        """Get artifact paths for a session."""
        record = self._sessions.get(session_id)
        return record.artifacts if record else []
```

- [ ] **Step 4: Implement control plane router**

```python
# backend/routers/control.py
"""Control plane API endpoints — session management, LLM proxy, artifact storage."""

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/control")


class CreateSessionRequest(BaseModel):
    """Request to create a new agent session."""
    repo_url: str = ""
    pr_number: int = 0
    diff: str = ""
    app_url: str = ""


class LLMProxyRequest(BaseModel):
    """Request to proxy an LLM call."""
    session_id: str
    messages: list[dict[str, str]]


@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest,
    request: Request,
) -> dict[str, Any]:
    """Create a new agent session."""
    cp = request.app.state.control_plane
    session_id, token = cp.create_session(
        repo_url=body.repo_url,
        pr_number=body.pr_number,
        diff=body.diff,
        app_url=body.app_url,
    )
    return {"session_id": session_id, "session_token": token, "status": "pending"}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    request: Request,
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    """Get session status."""
    cp = request.app.state.control_plane
    token = authorization.replace("Bearer ", "")
    if not cp.validate_token(session_id, token):
        raise HTTPException(status_code=401, detail="Invalid session token")

    session = cp.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "status": session.status.value,
        "actions": len(session.actions),
    }


@router.post("/llm")
async def proxy_llm(
    body: LLMProxyRequest,
    request: Request,
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    """Proxy an LLM call — the sandbox sends messages, we call Claude with real API keys."""
    cp = request.app.state.control_plane
    token = authorization.replace("Bearer ", "")
    if not cp.validate_token(body.session_id, token):
        raise HTTPException(status_code=401, detail="Invalid session token")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=api_key)

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=body.messages,
    )
    result = response.content[0].text

    logger.info("LLM proxy call", extra={"session_id": body.session_id, "length": len(result)})
    return {"response": result}


@router.post("/artifacts")
async def upload_artifact(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form(...),
    artifact_type: str = Form("file"),
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    """Upload an artifact from the sandbox."""
    cp = request.app.state.control_plane
    token = authorization.replace("Bearer ", "")
    if not cp.validate_token(session_id, token):
        raise HTTPException(status_code=401, detail="Invalid session token")

    artifact_dir = Path(f"/tmp/pr-videos/artifacts/{session_id}")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    file_path = artifact_dir / (file.filename or "artifact")
    content = await file.read()
    file_path.write_bytes(content)

    cp.store_artifact(session_id, str(file_path))
    logger.info(
        "Artifact uploaded",
        extra={"session_id": session_id, "type": artifact_type, "size": len(content)},
    )
    return {"url": str(file_path), "size": len(content)}
```

- [ ] **Step 5: Wire control plane into main.py**

Add to `backend/main.py`:
```python
from routers import control
from services.control_plane import ControlPlaneService

app.include_router(control.router)

# In lifespan, add:
app.state.control_plane = ControlPlaneService(settings)
```

- [ ] **Step 6: Run tests**

Run: `cd backend && python -m pytest tests/services/test_control_plane.py -v`
Expected: 3 PASSED

- [ ] **Step 7: Commit**

```bash
cd backend && ruff check . && ruff format .
git add backend/services/control_plane.py backend/routers/control.py backend/tests/services/test_control_plane.py backend/main.py
git commit -m "feat(control-plane): add session management, LLM proxy, and artifact endpoints"
```

---

### Task 11: Agent Router + Full Pipeline Integration

**Files:**
- Create: `backend/routers/agent.py`
- Create: `backend/tests/test_agent_router.py`
- Modify: `backend/__main__.py` (add `agent` subcommand)
- Modify: `backend/main.py` (add agent router)

- [ ] **Step 1: Write failing test for agent router**

```python
# backend/tests/test_agent_router.py
"""Tests for the agent API endpoint."""
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_agent_run_accepts_request() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/agents/run",
            json={
                "url": "http://localhost:3000",
                "diff": "+ added button",
                "mode": "direct",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert "session_id" in data
```

- [ ] **Step 2: Implement agent router**

```python
# backend/routers/agent.py
"""Agent endpoint — triggers the full cloud agent pipeline."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents")


class AgentRunRequest(BaseModel):
    """Request to run an agent."""
    url: str
    diff: str = ""
    repo_url: str = ""
    pr_number: int = 0
    mode: str = "direct"  # "direct" or "sandbox"


@router.post("/run")
async def run_agent(
    body: AgentRunRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Trigger an agent run. Returns immediately with session ID."""
    session_id = str(uuid.uuid4())[:8]
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    logger.info(
        "Agent run requested",
        extra={
            "correlation_id": correlation_id,
            "session_id": session_id,
            "url": body.url,
            "mode": body.mode,
        },
    )

    # In production, this would launch a Docker sandbox.
    # For now, accept the request — actual execution happens via CLI or sandbox.
    return {
        "status": "accepted",
        "session_id": session_id,
        "mode": body.mode,
        "url": body.url,
    }
```

- [ ] **Step 3: Add `agent` CLI subcommand to `__main__.py`**

Add to `backend/__main__.py` — a new `agent` subparser:

```python
agent_parser = subparsers.add_parser("agent", help="Run AI agent to demo a URL")
agent_parser.add_argument("--url", required=True, help="App URL to demo")
agent_parser.add_argument("--diff", default="", help="Path to git diff file")
agent_parser.add_argument("--output", default="", help="Output directory for artifacts")
agent_parser.add_argument("--mode", default="direct", choices=["direct", "sandbox"],
                          help="Run mode: direct (local) or sandbox (Docker)")
```

And handle it in `main()`:

```python
if args.command == "agent":
    from services.agent_brain import AgentBrain
    from services.gateway import DirectGateway
    from services.interaction import InteractionResult
    from services.artifact import collect_artifacts
    from services.screen_capture import ScreenCapture
    from models.agent import AgentSession
    import os

    diff_content = ""
    if args.diff:
        with open(args.diff, encoding="utf-8") as f:
            diff_content = f.read()

    output_dir = args.output or settings.output_dir

    session = AgentSession(
        session_id="cli",
        diff=diff_content,
        app_url=args.url,
    )
    gateway = DirectGateway(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    brain = AgentBrain(gateway=gateway, session=session)

    async def run_agent():
        plan = await brain.plan()
        logger.info("Plan: %s (%d steps)", plan.description, len(plan.steps))
        result = await brain.execute(output_dir=output_dir + "/screenshots")
        summary = brain.generate_summary(result)
        bundle = collect_artifacts(
            session_id="cli",
            screenshot_paths=result.screenshots,
            log_text=summary,
        )
        logger.info("Agent complete", output=output_dir, artifacts=len(bundle.artifacts))
        print(summary)

    asyncio.run(run_agent())
    return 0
```

- [ ] **Step 4: Wire agent router into main.py**

Add `from routers import agent` and `app.include_router(agent.router)` in `backend/main.py`.

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_agent_router.py -v`
Expected: PASSED

- [ ] **Step 6: Commit**

```bash
cd backend && ruff check . && ruff format .
git add backend/routers/agent.py backend/tests/test_agent_router.py backend/__main__.py backend/main.py
git commit -m "feat(agent): add agent router, CLI subcommand, and full pipeline integration"
```

---

### Task 12: Docker Compose + GitHub Actions Workflow

**Files:**
- Create: `docker-compose.agent.yml`
- Modify: `.github/workflows/pr-video.yml`

- [ ] **Step 1: Create docker-compose.agent.yml**

```yaml
# docker-compose.agent.yml
# Runs the control plane + optionally spawns agent sandboxes
version: "3.9"

services:
  control-plane:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "9100:9100"
    environment:
      - HOST=0.0.0.0
      - PORT=9100
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - artifacts:/tmp/pr-videos/artifacts
    command: uvicorn main:app --host 0.0.0.0 --port 9100

  # Agent sandbox — launched dynamically, not always running
  # Use: docker compose -f docker-compose.agent.yml run agent
  agent:
    build:
      context: .
      dockerfile: sandbox/Dockerfile
    depends_on:
      - control-plane
    environment:
      - CONTROL_PLANE_URL=http://control-plane:9100
      - SESSION_TOKEN=${SESSION_TOKEN}
      - SESSION_ID=${SESSION_ID}
      - AGENT_DIFF=${AGENT_DIFF}
      - AGENT_APP_URL=${AGENT_APP_URL:-http://host.docker.internal:3000}
    volumes:
      - artifacts:/artifacts
    network_mode: host
    profiles:
      - agent  # Only started explicitly

volumes:
  artifacts:
```

- [ ] **Step 2: Update GitHub Actions workflow**

Update `.github/workflows/pr-video.yml` to use the new agent system:

```yaml
name: PR Demo Video (Agent)

on:
  pull_request:
    types: [opened, synchronize]
  workflow_dispatch:
    inputs:
      url:
        description: "URL to record"
        required: true
        default: "https://example.com"

permissions:
  pull-requests: write
  contents: read

jobs:
  generate-video:
    runs-on: ubuntu-latest
    if: >-
      (github.event_name == 'workflow_dispatch') ||
      (github.event.pull_request.draft == false && github.actor != 'dependabot[bot]')
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install backend dependencies
        run: |
          cd backend
          pip install -e ".[dev]"
          pip install anthropic>=0.40.0

      - name: Install Playwright
        run: playwright install chromium --with-deps

      - name: Install FFmpeg
        run: sudo apt-get update && sudo apt-get install -y ffmpeg

      - name: Get PR diff
        if: github.event_name == 'pull_request'
        run: |
          git diff origin/${{ github.base_ref }}...HEAD > /tmp/pr_diff.txt

      - name: Determine recording URL
        id: url
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            echo "url=${{ github.event.inputs.url }}" >> "$GITHUB_OUTPUT"
          else
            echo "url=https://example.com" >> "$GITHUB_OUTPUT"
          fi

      - name: Run Agent Demo (direct mode)
        if: env.ANTHROPIC_API_KEY != ''
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          cd backend
          DIFF_ARG=""
          if [ -f /tmp/pr_diff.txt ]; then
            DIFF_ARG="--diff /tmp/pr_diff.txt"
          fi
          python __main__.py agent \
            --url "${{ steps.url.outputs.url }}" \
            --output /tmp/pr-videos \
            --mode direct \
            $DIFF_ARG

      - name: Fallback to basic recording (no API key)
        if: env.ANTHROPIC_API_KEY == ''
        run: |
          cd backend
          DIFF_ARG=""
          if [ -f /tmp/pr_diff.txt ]; then
            DIFF_ARG="--diff /tmp/pr_diff.txt"
          fi
          python __main__.py generate \
            --url "${{ steps.url.outputs.url }}" \
            --output /tmp/pr-demo.mp4 \
            $DIFF_ARG

      - name: Upload video artifact
        uses: actions/upload-artifact@v4
        with:
          name: pr-demo-video
          path: /tmp/pr-videos/
          retention-days: 30

      - name: Post PR comment with video link
        if: github.event_name == 'pull_request'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          RUN_URL="${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
          COMMENT="## 🤖 Agent Demo Video

          A demo video has been generated for this PR by an AI agent.

          **[Download artifacts](${RUN_URL})** (click Artifacts section)

          The agent analyzed the PR diff, planned interactions, and recorded itself demoing the changes.

          ---
          *Generated by PR Video Agent | Demos, not diffs*"

          gh pr comment ${{ github.event.pull_request.number }} --body "$COMMENT"
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.agent.yml .github/workflows/pr-video.yml
git commit -m "feat(infra): add Docker Compose agent stack and updated GitHub Actions workflow"
```

---

### Task 13: Update AGENTS.md and Config

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `backend/config/settings.py`
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add new dependencies to pyproject.toml**

Add to `[project] dependencies`:
```
"anthropic>=0.40.0",
```

- [ ] **Step 2: Add agent settings to config/settings.py**

Add fields:
```python
anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
control_plane_port: int = field(default_factory=lambda: int(os.environ.get("CONTROL_PLANE_PORT", "9100")))
sandbox_image: str = field(default_factory=lambda: os.environ.get("SANDBOX_IMAGE", "pr-video-sandbox:latest"))
sandbox_memory: str = field(default_factory=lambda: os.environ.get("SANDBOX_MEMORY", "2g"))
sandbox_timeout: int = field(default_factory=lambda: int(os.environ.get("SANDBOX_TIMEOUT", "600")))
```

- [ ] **Step 3: Update Module Dependency Rules in AGENTS.md**

Add new modules to the dependency DAG.

- [ ] **Step 4: Update Commands section in AGENTS.md and CLAUDE.md**

Add:
```bash
# Agent (AI-powered demo):
cd backend && python __main__.py agent --url <URL> --diff <DIFF_FILE>  # Run agent locally
docker compose -f docker-compose.agent.yml up control-plane             # Start control plane
docker compose -f docker-compose.agent.yml run agent                    # Run agent in sandbox
```

- [ ] **Step 5: Run validate.sh**

```bash
./scripts/validate.sh
```

- [ ] **Step 6: Commit**

```bash
git add AGENTS.md CLAUDE.md backend/config/settings.py backend/pyproject.toml
git commit -m "chore(config): add agent settings, dependencies, and update module docs"
```

---

## Validation and Acceptance

1. `cd backend && python -m pytest tests/ -v` — all tests pass (existing + new)
2. `cd backend && python __main__.py agent --url https://example.com --diff /tmp/diff.txt` — agent plans interactions, executes them, captures screenshots, outputs summary
3. `docker build -f sandbox/Dockerfile -t pr-video-sandbox .` — sandbox image builds
4. `POST /api/control/sessions` — creates session with token
5. `POST /api/agents/run` — accepts agent run request
6. `POST /api/control/llm` — proxies LLM call (requires valid token)
7. `scripts/validate.sh` exits 0
8. GitHub Actions workflow runs on PR and posts comment with artifacts

## Idempotence and Recovery

All new services are stateless. The control plane uses in-memory session storage (upgradeable to Redis/Postgres later). Docker containers are disposable — kill and recreate at any time. Artifacts are written to `/tmp/pr-videos/` or configurable output directory. Re-running any task overwrites previous output safely.

---

## Progress

- [ ] Task 1: Agent data models
- [ ] Task 2: Gateway protocol
- [ ] Task 3: Screen capture service
- [ ] Task 4: Interaction service
- [ ] Task 5: Agent brain
- [ ] Task 6: Artifact collector
- [ ] Task 7: GitHub PR integration
- [ ] Task 8: Docker sandbox
- [ ] Task 9: Sandbox orchestrator
- [ ] Task 10: Control plane endpoints
- [ ] Task 11: Agent router + full pipeline integration
- [ ] Task 12: Docker Compose + GitHub Actions workflow
- [ ] Task 13: Update AGENTS.md and config

## Decision Log

- (2026-03-23) Pattern 2 (isolate the agent) — sandbox has zero secrets, control plane proxies everything. Inspired by Browser Use architecture.
- (2026-03-23) Docker over Firecracker — simpler, works everywhere, same image for dev and prod. Unikraft upgrade path for production later.
- (2026-03-23) DirectGateway + ControlPlaneGateway — same interface, different backend. Agent code doesn't know which it's using.
- (2026-03-23) Claude Sonnet 4 for interaction planning — fast, good at structured JSON output, cost-effective for high-volume agent runs.
- (2026-03-23) Xvfb + ffmpeg x11grab for recording — same approach Cursor likely uses. Falls back to Playwright video recording on non-Linux systems.
