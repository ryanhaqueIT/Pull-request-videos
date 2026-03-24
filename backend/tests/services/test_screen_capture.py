"""Tests for the screen capture service."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.screen_capture import ScreenCapture


@pytest.fixture
def capture(tmp_path: Path) -> ScreenCapture:
    return ScreenCapture(output_dir=str(tmp_path), display=":99")


def test_screen_capture_init(capture: ScreenCapture) -> None:
    assert capture.display == ":99"
    assert not capture.is_recording


@patch("services.screen_capture.subprocess.Popen")
@patch("services.screen_capture.shutil.which", return_value="/usr/bin/ffmpeg")
def test_start_recording_launches_ffmpeg(
    mock_which: MagicMock, mock_popen: MagicMock, capture: ScreenCapture
) -> None:
    mock_popen.return_value.pid = 12345
    capture.start_recording()
    assert capture.is_recording
    mock_popen.assert_called_once()
    cmd = mock_popen.call_args[0][0]
    assert "ffmpeg" in cmd[0]
    assert "-f" in cmd
    assert "x11grab" in cmd


@patch("services.screen_capture.subprocess.Popen")
@patch("services.screen_capture.shutil.which", return_value="/usr/bin/ffmpeg")
def test_stop_recording_returns_path(
    mock_which: MagicMock, mock_popen: MagicMock, capture: ScreenCapture
) -> None:
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    mock_proc.poll.return_value = None
    mock_proc.communicate.return_value = (b"", b"")
    mock_popen.return_value = mock_proc
    capture.start_recording()
    path = capture.stop_recording()
    assert path.endswith(".mp4")
    assert not capture.is_recording


def test_fallback_mode_uses_playwright(tmp_path: Path) -> None:
    """When Xvfb is not available, should indicate fallback mode."""
    cap = ScreenCapture(output_dir=str(tmp_path), display=":99", fallback_mode=True)
    assert cap.fallback_mode
