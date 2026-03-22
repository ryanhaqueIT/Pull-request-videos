"""Tests for the FFmpeg assembler service."""

from pathlib import Path
from unittest.mock import patch

import pytest

from services.assembler import assemble_video


def test_assemble_video_calls_ffmpeg(tmp_path: Path) -> None:
    """assemble_video invokes ffmpeg with correct arguments."""
    video_file = tmp_path / "input.webm"
    video_file.write_bytes(b"fake video content")
    output_file = tmp_path / "output.mp4"

    with patch("services.assembler.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        # Create the output file to simulate ffmpeg
        output_file.write_bytes(b"fake mp4")

        result = assemble_video(video_file, None, output_file)

        assert mock_run.called
        cmd_args = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd_args[0].lower()
        assert str(video_file) in cmd_args
        assert str(output_file) in cmd_args
        assert result == output_file


def test_assemble_video_with_audio(tmp_path: Path) -> None:
    """assemble_video includes audio track when audio_path provided."""
    video_file = tmp_path / "input.webm"
    video_file.write_bytes(b"fake video")
    audio_file = tmp_path / "narration.mp3"
    audio_file.write_bytes(b"fake audio")
    output_file = tmp_path / "output.mp4"

    with patch("services.assembler.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        output_file.write_bytes(b"fake mp4 with audio")

        assemble_video(video_file, audio_file, output_file)

        cmd_args = mock_run.call_args[0][0]
        assert str(audio_file) in cmd_args
        assert "-shortest" in cmd_args


def test_assemble_video_ffmpeg_failure(tmp_path: Path) -> None:
    """assemble_video raises RuntimeError when ffmpeg fails."""
    video_file = tmp_path / "input.webm"
    video_file.write_bytes(b"fake video")
    output_file = tmp_path / "output.mp4"

    with patch("services.assembler.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "encoding error"

        with pytest.raises(RuntimeError, match="FFmpeg failed"):
            assemble_video(video_file, None, output_file)
