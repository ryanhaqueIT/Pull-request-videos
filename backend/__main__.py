"""CLI entry point: cd backend && python __main__.py generate --url <URL>."""

import argparse
import asyncio
import logging
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

    args = parser.parse_args()

    if args.command != "generate":
        parser.print_help()
        return 1

    setup_cli_logging()
    logger = structlog.get_logger()

    settings = load_settings()

    diff_content = ""
    if args.diff:
        try:
            with open(args.diff, encoding="utf-8") as f:
                diff_content = f.read()
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


if __name__ == "__main__":
    sys.exit(main())
