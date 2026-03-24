# backend/services/artifact.py
"""Collects and packages all agent artifacts into a bundle."""

import logging
from pathlib import Path

from models.artifact import Artifact, ArtifactBundle

logger = logging.getLogger(__name__)


def collect_artifacts(
    session_id: str,
    video_path: str = "",
    screenshot_paths: list[str] | None = None,
    log_text: str = "",
    narration_text: str = "",
    narration_audio_path: str = "",
) -> ArtifactBundle:
    """Collect all artifacts from an agent session into a bundle."""
    artifacts: list[Artifact] = []
    ss_paths = screenshot_paths or []

    if video_path and Path(video_path).exists():
        size = Path(video_path).stat().st_size
        artifacts.append(
            Artifact(
                artifact_type="video",
                path=video_path,
                description="Demo video",
                size_bytes=size,
            )
        )
        logger.info("Video artifact collected", extra={"path": video_path, "size": size})

    for ss in ss_paths:
        if Path(ss).exists():
            size = Path(ss).stat().st_size
            artifacts.append(
                Artifact(
                    artifact_type="screenshot",
                    path=ss,
                    description=Path(ss).stem,
                    size_bytes=size,
                )
            )

    if log_text:
        artifacts.append(
            Artifact(
                artifact_type="log",
                path="",
                description="Agent log",
                size_bytes=len(log_text),
            )
        )

    if narration_audio_path and Path(narration_audio_path).exists():
        size = Path(narration_audio_path).stat().st_size
        artifacts.append(
            Artifact(
                artifact_type="narration",
                path=narration_audio_path,
                description="Narration audio",
                size_bytes=size,
            )
        )

    logger.info(
        "Artifacts collected",
        extra={"session_id": session_id, "count": len(artifacts)},
    )

    return ArtifactBundle(
        session_id=session_id,
        video_path=video_path,
        screenshot_paths=ss_paths,
        log_text=log_text,
        narration_text=narration_text,
        narration_audio_path=narration_audio_path,
        artifacts=artifacts,
    )
