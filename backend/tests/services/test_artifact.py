# backend/tests/services/test_artifact.py
"""Tests for the artifact collector."""

from pathlib import Path

from models.artifact import ArtifactBundle
from services.artifact import collect_artifacts


def test_collect_artifacts_with_video(tmp_path: Path) -> None:
    video = tmp_path / "session.mp4"
    video.write_bytes(b"\x00" * 1024)
    ss1 = tmp_path / "screenshot-001.png"
    ss1.write_bytes(b"\x89PNG" + b"\x00" * 100)

    bundle = collect_artifacts(
        session_id="s1",
        video_path=str(video),
        screenshot_paths=[str(ss1)],
        log_text="agent started\nagent finished",
    )

    assert bundle.session_id == "s1"
    assert bundle.video_path == str(video)
    assert len(bundle.screenshot_paths) == 1
    assert len(bundle.artifacts) == 3  # video + screenshot + log


def test_collect_artifacts_no_video(tmp_path: Path) -> None:
    bundle = collect_artifacts(
        session_id="s2",
        video_path="",
        screenshot_paths=[],
        log_text="no video recorded",
    )

    assert bundle.video_path == ""
    assert len(bundle.artifacts) == 1  # log only


def test_artifact_bundle_summary() -> None:
    bundle = ArtifactBundle(session_id="s3", summary="Test summary")
    assert bundle.summary == "Test summary"
