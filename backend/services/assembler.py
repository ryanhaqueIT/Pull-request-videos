"""FFmpeg video assembler. Combines screen recording with narration audio."""

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _find_ffmpeg() -> str:
    """Find ffmpeg binary. Checks system PATH first, then imageio-ffmpeg fallback."""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    return "ffmpeg"


def assemble_video(
    video_path: Path,
    audio_path: Path | None,
    output_path: Path,
) -> Path:
    """Combine a WebM video with an optional MP3 audio track into final MP4.

    Uses FFmpeg subprocess. If audio_path is None, converts video only.
    Returns the path to the output MP4.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = _find_ffmpeg()

    if audio_path and audio_path.exists():
        # Combine video + audio
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    else:
        # Video only
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(video_path),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-an",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

    logger.info("Assembling video", extra={"cmd": " ".join(cmd)})

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        logger.error(
            "FFmpeg failed",
            extra={"returncode": result.returncode, "stderr": result.stderr[:500]},
        )
        msg = f"FFmpeg failed with exit code {result.returncode}: {result.stderr[:200]}"
        raise RuntimeError(msg)

    logger.info(
        "Assembly complete",
        extra={"output": str(output_path), "size": output_path.stat().st_size},
    )
    return output_path
