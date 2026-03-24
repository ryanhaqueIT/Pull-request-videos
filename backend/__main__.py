"""CLI entry point: cd backend && python __main__.py generate --url <URL>."""

import argparse
import asyncio
import logging
import os
import sys

import structlog

from config.settings import load_settings
from models.video import VideoRequest
from services.pipeline import generate_video


def setup_cli_logging() -> None:
    """Configure logging for CLI usage."""
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def _read_diff_file(path: str) -> str:
    """Read a diff file and return its content."""
    with open(path, encoding="utf-8") as f:
        return f.read()


def _run_generate(args: argparse.Namespace) -> int:
    """Run the basic video generation pipeline."""
    setup_cli_logging()
    logger = structlog.get_logger()
    settings = load_settings()

    diff_content = ""
    if args.diff:
        try:
            diff_content = _read_diff_file(args.diff)
        except OSError as e:
            logger.error("Failed to read diff file", error=str(e))
            return 1

    request = VideoRequest(
        url=args.url,
        diff=diff_content,
        output_path=args.output,
    )

    logger.info("Starting video generation", url=args.url)
    result = asyncio.run(generate_video(request, settings))

    if result.status.value == "failed":
        logger.error("Video generation failed", error=result.error)
        return 1

    logger.info(
        "Video generation complete",
        output=result.output_path,
        size_bytes=result.file_size_bytes,
        stages=result.stages_completed,
    )
    return 0


def _run_agent(args: argparse.Namespace) -> int:
    """Run the AI agent to demo a URL interactively."""
    setup_cli_logging()
    logger = structlog.get_logger()
    settings = load_settings()

    diff_content = ""
    if args.diff:
        try:
            diff_content = _read_diff_file(args.diff)
        except OSError as e:
            logger.error("Failed to read diff file", error=str(e))
            return 1

    output_dir = args.output or settings.output_dir

    from models.agent import AgentSession
    from services.agent_brain import AgentBrain
    from services.artifact import collect_artifacts
    from services.gateway import DirectGateway

    session = AgentSession(
        session_id="cli",
        diff=diff_content,
        app_url=args.url,
    )
    gateway = DirectGateway(api_key=settings.anthropic_api_key)
    brain = AgentBrain(gateway=gateway, session=session)

    async def run_agent_loop() -> int:
        # Phase 1: Plan
        logger.info("Phase 1: Planning interaction...")
        plan = await brain.plan()
        logger.info("Plan generated", description=plan.description, steps=len(plan.steps))

        # Phase 2: Execute
        logger.info("Phase 2: Executing interaction plan...")
        result = await brain.execute(output_dir=output_dir + "/screenshots")
        logger.info(
            "Execution complete",
            steps_completed=result.steps_completed,
            total_steps=result.total_steps,
            screenshots=len(result.screenshots),
        )

        # Phase 3: Produce demo video (WebM → MP4 with narration)
        logger.info("Phase 3: Producing demo video...")
        video_output = os.path.join(output_dir, "demo-video.mp4")
        video_path = await brain.produce_video(result, output_path=video_output)

        # Phase 4: Collect artifacts
        logger.info("Phase 4: Collecting artifacts...")
        summary = brain.generate_summary(result, video_path=video_path)
        bundle = collect_artifacts(
            session_id="cli",
            video_path=video_path,
            screenshot_paths=result.screenshots,
            log_text=summary,
        )

        logger.info("Agent complete", artifacts=len(bundle.artifacts))
        logger.info("Summary:\n" + summary)
        if video_path:
            logger.info("Demo video produced", path=video_path)
        return 0

    return asyncio.run(run_agent_loop())


def main() -> int:
    """CLI main entry point."""
    parser = argparse.ArgumentParser(
        prog="pr_video",
        description="Generate demo videos from URLs and PR diffs",
    )
    subparsers = parser.add_subparsers(dest="command")

    gen_parser = subparsers.add_parser("generate", help="Generate a video from a URL")
    gen_parser.add_argument("--url", required=True, help="URL to record")
    gen_parser.add_argument("--diff", default="", help="Path to git diff file")
    gen_parser.add_argument("--output", default="", help="Output MP4 path")

    agent_parser = subparsers.add_parser("agent", help="Run AI agent to demo a URL")
    agent_parser.add_argument("--url", required=True, help="App URL to demo")
    agent_parser.add_argument("--diff", default="", help="Path to git diff file")
    agent_parser.add_argument("--output", default="", help="Output directory for artifacts")
    agent_parser.add_argument(
        "--mode",
        default="direct",
        choices=["direct", "sandbox"],
        help="Run mode: direct (local) or sandbox (Docker)",
    )

    args = parser.parse_args()

    if args.command == "generate":
        return _run_generate(args)
    if args.command == "agent":
        return _run_agent(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
