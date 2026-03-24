"""Claude-powered agent brain — the reasoning loop.

Given a diff and a running app, the agent:
1. Analyzes what changed (PLANNING)
2. Generates an interaction plan (PLANNING)
3. Executes the plan via Playwright while recording video (INTERACTING)
4. Assembles final MP4 with narration (RECORDING)
5. Summarizes results (COLLECTING)
"""

import logging
import time
from pathlib import Path

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
            extra={
                "session_id": self._session.session_id,
                "app_url": self._session.app_url,
            },
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
            extra={
                "session_id": self._session.session_id,
                "steps": len(plan.steps),
            },
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

    async def produce_video(
        self,
        result: InteractionResult,
        output_path: str = "",
    ) -> str:
        """Phase 3: Assemble the raw recording into a final MP4 with narration.

        Takes the WebM recorded by Playwright, generates narration from the diff,
        synthesizes speech, and assembles everything into a polished MP4.
        Returns the path to the final video.
        """
        self._session.status = AgentStatus.RECORDING
        start = time.time()

        if not result.video_path or not Path(result.video_path).exists():
            logger.warning("No video recording found — skipping assembly")
            return ""

        from config.settings import load_settings
        from services.assembler import assemble_video
        from services.narrator import generate_narration_script, synthesize_speech

        settings = load_settings()
        output = (
            Path(output_path)
            if output_path
            else (Path(result.video_path).parent.parent / "demo-video.mp4")
        )

        # Generate narration from the diff
        audio_path = None
        if self._session.diff:
            logger.info("Generating narration from diff...")
            script = generate_narration_script(self._session.diff)
            audio_path = await synthesize_speech(script, settings)
            logger.info(
                "Narration generated",
                extra={"script_length": len(script), "audio": str(audio_path)},
            )

        # Assemble: raw WebM recording + narration audio → final MP4
        logger.info("Assembling final video...")
        final_path = assemble_video(
            video_path=Path(result.video_path),
            audio_path=audio_path,
            output_path=output,
        )

        file_size = final_path.stat().st_size
        self._session.actions.append(
            AgentAction(
                action_type=AgentActionType.COLLECT_ARTIFACTS,
                description=f"Produced demo video: {final_path.name} ({file_size:,} bytes)",
                duration_seconds=time.time() - start,
            )
        )

        logger.info(
            "Demo video produced",
            extra={"output": str(final_path), "size": file_size},
        )
        return str(final_path)

    def generate_summary(self, result: InteractionResult, video_path: str = "") -> str:
        """Generate a human-readable summary of the agent's work."""
        plan = self._session.interaction_plan
        plan_desc = plan.description if plan else "No plan"

        lines = [
            "## Agent Demo Summary",
            "",
            f"**What was demoed:** {plan_desc}",
            f"**Steps completed:** {result.steps_completed}/{result.total_steps}",
            f"**Screenshots captured:** {len(result.screenshots)}",
            f"**Duration:** {result.duration_seconds:.1f}s",
        ]

        if video_path:
            size = Path(video_path).stat().st_size if Path(video_path).exists() else 0
            lines.append(f"**Demo video:** {Path(video_path).name} ({size:,} bytes)")

        if result.errors:
            lines.append("")
            lines.append("**Issues encountered:**")
            for err in result.errors:
                lines.append(f"- {err}")

        actions = self._session.actions
        if actions:
            lines.append("")
            lines.append("**Agent actions:**")
            for a in actions:
                lines.append(f"- {a.action_type.value}: {a.description}")

        return "\n".join(lines)
