"""Application configuration — the single source of truth for env vars.

Only this module may read os.environ. All other modules import from here.
See docs/design-docs/core-beliefs.md #2 (Configuration Is Not Code).
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from environment variables."""

    host: str = field(default_factory=lambda: os.environ.get("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.environ.get("PORT", "8000")))
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))
    output_dir: str = field(default_factory=lambda: os.environ.get("OUTPUT_DIR", "/tmp/pr-videos"))
    tts_voice: str = field(default_factory=lambda: os.environ.get("TTS_VOICE", "en-US-AriaNeural"))
    browser_timeout_ms: int = field(
        default_factory=lambda: int(os.environ.get("BROWSER_TIMEOUT_MS", "30000"))
    )
    video_width: int = field(default_factory=lambda: int(os.environ.get("VIDEO_WIDTH", "1280")))
    video_height: int = field(default_factory=lambda: int(os.environ.get("VIDEO_HEIGHT", "720")))


def load_settings() -> Settings:
    """Load settings from environment. Fails fast if required vars are missing."""
    return Settings()
