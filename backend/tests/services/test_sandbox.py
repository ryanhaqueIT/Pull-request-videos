"""Tests for the Docker sandbox orchestrator."""

from unittest.mock import MagicMock, patch

import pytest

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
    mock_run.return_value = MagicMock(returncode=0, stdout="abc123container\n", stderr="")
    container_id = orchestrator.create(
        session_id="s1",
        control_plane_url="http://host:9100",
        session_token="tok-123",
    )
    assert container_id == "abc123container"
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "docker"
    assert "run" in cmd


@patch("services.sandbox.subprocess.run")
def test_create_sandbox_failure(mock_run: MagicMock, orchestrator: SandboxOrchestrator) -> None:
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="image not found")
    with pytest.raises(RuntimeError, match="Docker run failed"):
        orchestrator.create(
            session_id="s2",
            control_plane_url="http://host:9100",
            session_token="tok-456",
        )


@patch("services.sandbox.subprocess.run")
def test_get_logs(mock_run: MagicMock, orchestrator: SandboxOrchestrator) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="agent started\nagent done\n", stderr="")
    logs = orchestrator.get_logs("abc123")
    assert "agent started" in logs


@patch("services.sandbox.subprocess.run")
def test_get_status(mock_run: MagicMock, orchestrator: SandboxOrchestrator) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="running\n", stderr="")
    status = orchestrator.get_status("abc123")
    assert status == "running"


@patch("services.sandbox.subprocess.run")
def test_stop_sandbox(mock_run: MagicMock, orchestrator: SandboxOrchestrator) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    orchestrator.stop("abc123")
    assert mock_run.call_count == 2  # stop + rm
