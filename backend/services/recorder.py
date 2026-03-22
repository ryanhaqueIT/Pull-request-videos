"""Playwright-based screen recorder. Records a browser session as WebM video."""

import logging
from pathlib import Path

from config.settings import Settings
from models.video import VideoRequest

logger = logging.getLogger(__name__)


async def record_url(request: VideoRequest, settings: Settings) -> Path:
    """Record a browser session visiting the given URL.

    Launches headless Chromium via Playwright, navigates to the URL,
    scrolls through the page, and saves the recording as WebM.

    Returns the path to the recorded WebM file.
    """
    output_dir = Path(settings.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": settings.video_width, "height": settings.video_height},
            record_video_dir=str(output_dir),
            record_video_size={
                "width": settings.video_width,
                "height": settings.video_height,
            },
        )
        page = await context.new_page()

        logger.info("Recording started", extra={"url": request.url})

        await page.goto(request.url, timeout=settings.browser_timeout_ms)
        await page.wait_for_load_state("networkidle", timeout=settings.browser_timeout_ms)

        # Scroll through the page to capture content
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        await page.wait_for_timeout(1000)
        await page.evaluate("window.scrollTo(0, (document.body.scrollHeight * 2) / 3)")
        await page.wait_for_timeout(1000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        video_path_str = await page.video.path()
        await context.close()
        await browser.close()

    video_path = Path(video_path_str)
    logger.info(
        "Recording complete",
        extra={"url": request.url, "output": str(video_path), "size": video_path.stat().st_size},
    )
    return video_path
