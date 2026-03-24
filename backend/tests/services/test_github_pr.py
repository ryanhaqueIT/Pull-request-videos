"""Tests for GitHub PR integration."""

from models.artifact import ArtifactBundle
from services.github_pr import format_pr_comment


def test_format_pr_comment_with_all_artifacts() -> None:
    bundle = ArtifactBundle(
        session_id="s1",
        video_path="/tmp/demo.mp4",
        screenshot_paths=["/tmp/ss1.png", "/tmp/ss2.png"],
        log_text="agent started\n3 steps completed",
        summary="## Agent Demo Summary\n\nAdded submit button and verified it works.",
    )
    comment = format_pr_comment(
        bundle=bundle,
        artifact_url="https://github.com/repo/actions/runs/123",
    )
    assert "Agent Demo" in comment
    assert "Video" in comment or "video" in comment
    assert "screenshot" in comment.lower() or "Screenshot" in comment
    assert "https://github.com/repo/actions/runs/123" in comment


def test_format_pr_comment_no_video() -> None:
    bundle = ArtifactBundle(
        session_id="s2",
        summary="Quick fix, no video needed.",
    )
    comment = format_pr_comment(bundle=bundle, artifact_url="")
    assert "Quick fix" in comment


def test_format_pr_comment_with_errors() -> None:
    bundle = ArtifactBundle(
        session_id="s3",
        summary="## Agent Demo Summary\n\n**Issues encountered:**\n- Button not found",
    )
    comment = format_pr_comment(bundle=bundle, artifact_url="")
    assert "Issues" in comment or "Button not found" in comment
