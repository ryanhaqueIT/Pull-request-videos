# backend/models/artifact.py
"""Artifact data models. Leaf layer — no project imports."""

from dataclasses import dataclass, field


@dataclass
class Artifact:
    """A single artifact produced by an agent."""

    artifact_type: str  # "video", "screenshot", "log", "narration"
    path: str
    description: str = ""
    size_bytes: int = 0


@dataclass
class ArtifactBundle:
    """Collection of all artifacts from an agent session."""

    session_id: str
    video_path: str = ""
    screenshot_paths: list[str] = field(default_factory=list)
    log_text: str = ""
    narration_text: str = ""
    narration_audio_path: str = ""
    artifacts: list[Artifact] = field(default_factory=list)
    summary: str = ""
