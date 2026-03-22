"""Full video generation pipeline. Orchestrates recorder → narrator → assembler."""

import logging
from pathlib import Path

from config.settings import Settings
from models.video import VideoRequest, VideoResult, VideoStatus
from services.assembler import assemble_video
from services.narrator import generate_narration_script, synthesize_speech
from services.recorder import record_url

logger = logging.getLogger(__name__)


async def generate_video(request: VideoRequest, settings: Settings) -> VideoResult:
    """Run the full video generation pipeline.

    1. Record the URL with Playwright
    2. Generate narration from the diff
    3. Synthesize speech from narration
    4. Assemble final MP4

    Returns a VideoResult with the output path and metadata.
    """
    output_path = (
        Path(request.output_path)
        if request.output_path
        else (Path(settings.output_dir) / "output.mp4")
    )
    stages: list[str] = []

    try:
        # Stage 1: Record
        logger.info("Pipeline stage 1: Recording", extra={"url": request.url})
        video_path = await record_url(request, settings)
        stages.append("recording")

        # Stage 2: Narrate
        audio_path = None
        if request.diff:
            logger.info("Pipeline stage 2: Narrating")
            script = generate_narration_script(request.diff)
            audio_path = await synthesize_speech(script, settings)
            stages.append("narration")
        else:
            logger.info("Pipeline stage 2: Skipping narration (no diff provided)")

        # Stage 3: Assemble
        logger.info("Pipeline stage 3: Assembling")
        assemble_video(video_path, audio_path, output_path)
        stages.append("assembly")

        file_size = output_path.stat().st_size
        logger.info(
            "Pipeline complete",
            extra={"output": str(output_path), "size": file_size, "stages": stages},
        )

        return VideoResult(
            output_path=str(output_path),
            status=VideoStatus.COMPLETE,
            file_size_bytes=file_size,
            stages_completed=stages,
        )

    except Exception as e:
        logger.error("Pipeline failed", extra={"error": str(e), "stages_completed": stages})
        return VideoResult(
            output_path=str(output_path),
            status=VideoStatus.FAILED,
            error=str(e),
            stages_completed=stages,
        )
