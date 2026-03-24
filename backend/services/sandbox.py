"""Docker sandbox orchestrator — creates, manages, and stops agent containers.

Each agent runs in an isolated Docker container with:
- Its own filesystem (cloned repo in /workspace)
- Xvfb + ffmpeg for screen recording
- Playwright + Chromium for browser interaction
- Only 3 env vars: SESSION_TOKEN, CONTROL_PLANE_URL, SESSION_ID
"""

import logging
import os
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
        diff: str = "",
        app_url: str = "",
        memory_limit: str = "2g",
        cpu_count: int = 2,
    ) -> str:
        """Create and start an agent sandbox container. Returns container ID."""
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            f"pr-video-agent-{session_id}",
            "--memory",
            memory_limit,
            "--cpus",
            str(cpu_count),
            "-e",
            f"SESSION_TOKEN={session_token}",
            "-e",
            f"CONTROL_PLANE_URL={control_plane_url}",
            "-e",
            f"SESSION_ID={session_id}",
            "-e",
            f"AGENT_DIFF={diff[:5000]}",
            "-e",
            f"AGENT_APP_URL={app_url}",
            "--network",
            "host",
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

        artifacts = []
        for f in os.listdir(dest_dir):
            artifacts.append(os.path.join(dest_dir, f))
        logger.info("Artifacts copied", extra={"count": len(artifacts), "dest": dest_dir})
        return artifacts
