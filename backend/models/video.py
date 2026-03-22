"""Data models for the video pipeline. Leaf layer — no project imports."""

from dataclasses import dataclass, field
from enum import Enum


class VideoStatus(Enum):
    """Status of a video generation job."""

    PENDING = "pending"
    RECORDING = "recording"
    NARRATING = "narrating"
    ASSEMBLING = "assembling"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class VideoRequest:
    """Input to the video generation pipeline."""

    url: str
    diff: str = ""
    output_path: str = ""


@dataclass
class VideoResult:
    """Output of the video generation pipeline."""

    output_path: str
    status: VideoStatus = VideoStatus.COMPLETE
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    error: str = ""
    stages_completed: list[str] = field(default_factory=list)
