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
        self._output_path = str(Path(self.output_dir) / f"session-{int(time.time())}.mp4")
        ffmpeg = self._find_ffmpeg()

        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "x11grab",
            "-video_size",
            f"{self.width}x{self.height}",
            "-framerate",
            str(self.fps),
            "-i",
            self.display,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
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
