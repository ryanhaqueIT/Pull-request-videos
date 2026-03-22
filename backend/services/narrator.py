"""Narration service. Generates a spoken narration from a git diff.

Two stages:
1. Generate narration script from diff (simple template for MVP, AI upgrade later)
2. Synthesize speech via edge-tts (free Microsoft neural voices)
"""

import logging
import tempfile
from pathlib import Path

from config.settings import Settings

logger = logging.getLogger(__name__)


def generate_narration_script(diff: str) -> str:
    """Generate a narration script from a git diff.

    MVP: simple summary of what changed. Future: use Claude API for intelligent narration.
    """
    if not diff.strip():
        return "This video shows a walkthrough of the application."

    lines = diff.strip().splitlines()
    files_changed: list[str] = []
    additions = 0
    deletions = 0

    for line in lines:
        if line.startswith("diff --git"):
            parts = line.split(" b/")
            if len(parts) > 1:
                files_changed.append(parts[-1])
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1

    file_count = len(files_changed)
    file_list = ", ".join(files_changed[:3])
    if file_count > 3:
        file_list += f", and {file_count - 3} more files"

    script = f"This pull request changes {file_count} files: {file_list}. "
    script += f"It adds {additions} lines and removes {deletions} lines. "
    script += "Let me walk you through what changed."

    logger.info(
        "Narration script generated",
        extra={"file_count": file_count, "additions": additions, "deletions": deletions},
    )
    return script


async def synthesize_speech(text: str, settings: Settings) -> Path:
    """Convert text to speech using edge-tts. Returns path to MP3 file."""
    import edge_tts

    output_path = Path(tempfile.mktemp(suffix=".mp3", dir=settings.output_dir))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(text, settings.tts_voice)
    await communicate.save(str(output_path))

    logger.info(
        "Speech synthesized",
        extra={"output": str(output_path), "size": output_path.stat().st_size},
    )
    return output_path
