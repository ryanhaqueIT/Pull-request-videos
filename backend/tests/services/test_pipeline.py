"""Tests for the full pipeline orchestration."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from config.settings import Settings
from models.video import VideoRequest, VideoStatus
from services.pipeline import generate_video


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Create test settings with a temp output directory."""
    return Settings(output_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_pipeline_records_and_assembles(settings: Settings, tmp_path: Path) -> None:
    """Pipeline runs recording and assembly stages."""
    output_mp4 = tmp_path / "test_output.mp4"

    with (
        patch("services.pipeline.record_url", new_callable=AsyncMock) as mock_record,
        patch("services.pipeline.assemble_video") as mock_assemble,
    ):
        fake_webm = tmp_path / "recording.webm"
        fake_webm.write_bytes(b"fake webm")
        mock_record.return_value = fake_webm

        output_mp4.write_bytes(b"fake mp4 output")
        mock_assemble.return_value = output_mp4

        request = VideoRequest(url="https://example.com", output_path=str(output_mp4))
        result = await generate_video(request, settings)

        assert result.status == VideoStatus.COMPLETE
        assert "recording" in result.stages_completed
        assert "assembly" in result.stages_completed
        mock_record.assert_called_once()
        mock_assemble.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_with_diff_includes_narration(settings: Settings, tmp_path: Path) -> None:
    """Pipeline generates narration when diff is provided."""
    output_mp4 = tmp_path / "test_output.mp4"

    with (
        patch("services.pipeline.record_url", new_callable=AsyncMock) as mock_record,
        patch("services.pipeline.synthesize_speech", new_callable=AsyncMock) as mock_tts,
        patch("services.pipeline.assemble_video") as mock_assemble,
    ):
        fake_webm = tmp_path / "recording.webm"
        fake_webm.write_bytes(b"fake webm")
        mock_record.return_value = fake_webm

        fake_mp3 = tmp_path / "narration.mp3"
        fake_mp3.write_bytes(b"fake audio")
        mock_tts.return_value = fake_mp3

        output_mp4.write_bytes(b"fake mp4")
        mock_assemble.return_value = output_mp4

        request = VideoRequest(
            url="https://example.com",
            diff="diff --git a/file.py b/file.py\n+new line",
            output_path=str(output_mp4),
        )
        result = await generate_video(request, settings)

        assert result.status == VideoStatus.COMPLETE
        assert "narration" in result.stages_completed
        mock_tts.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_handles_failure_gracefully(settings: Settings, tmp_path: Path) -> None:
    """Pipeline returns FAILED status on error, doesn't crash."""
    with patch("services.pipeline.record_url", new_callable=AsyncMock) as mock_record:
        mock_record.side_effect = RuntimeError("Browser launch failed")

        request = VideoRequest(url="https://example.com")
        result = await generate_video(request, settings)

        assert result.status == VideoStatus.FAILED
        assert "Browser launch failed" in result.error
