"""Tests for the Playwright recording service."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from config.settings import Settings
from models.video import VideoRequest
from services.recorder import record_url


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Test settings with temp output directory."""
    return Settings(output_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_record_url_launches_browser(settings: Settings, tmp_path: Path) -> None:
    """record_url launches Playwright and navigates to the URL."""
    fake_video = tmp_path / "fake_video.webm"
    fake_video.write_bytes(b"fake webm content")

    mock_page = AsyncMock()
    mock_page.video.path = AsyncMock(return_value=str(fake_video))

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw_cm = AsyncMock()
    mock_pw_cm.__aenter__ = AsyncMock(return_value=mock_playwright)
    mock_pw_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("playwright.async_api.async_playwright", return_value=mock_pw_cm):
        request = VideoRequest(url="https://example.com")
        result = await record_url(request, settings)

        assert result == fake_video
        mock_page.goto.assert_called_once()
        mock_page.wait_for_load_state.assert_called_once()
