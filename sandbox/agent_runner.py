#!/usr/bin/env python3
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
        from services.gateway import DirectGateway

        gateway = DirectGateway(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    else:
        from services.gateway import ControlPlaneGateway

        gateway = ControlPlaneGateway(  # type: ignore[assignment]
            control_plane_url=control_plane_url,
            session_token=session_token,
            session_id=session_id,
        )

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

    except Exception:
        logger.exception("Agent failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
