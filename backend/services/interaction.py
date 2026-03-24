"""Playwright-based browser interaction service.

Executes an InteractionPlan: navigates, clicks, types, scrolls,
takes screenshots, and asserts text/visibility. Each step is logged.
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from models.agent import InteractionPlan, InteractionStep, StepType

logger = logging.getLogger(__name__)


@dataclass
class InteractionResult:
    """Result of executing an interaction plan."""

    steps_completed: int = 0
    total_steps: int = 0
    screenshots: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    video_path: str = ""  # Playwright records the browser session as WebM


async def _execute_step(
    page: object,  # playwright Page
    step: InteractionStep,
    output_dir: str,
    screenshot_count: int,
) -> tuple[str, str]:
    """Execute a single interaction step. Returns (screenshot_path, error)."""
    try:
        if step.step_type == StepType.NAVIGATE:
            await page.goto(step.target, timeout=step.timeout_ms)  # type: ignore[attr-defined]
            await page.wait_for_load_state("networkidle", timeout=step.timeout_ms)  # type: ignore[attr-defined]

        elif step.step_type == StepType.CLICK:
            await page.click(step.selector, timeout=step.timeout_ms)  # type: ignore[attr-defined]

        elif step.step_type == StepType.TYPE:
            await page.fill(step.selector, step.value, timeout=step.timeout_ms)  # type: ignore[attr-defined]

        elif step.step_type == StepType.SCROLL:
            direction = step.target or "down"
            scroll_map = {
                "down": "window.scrollBy(0, 500)",
                "up": "window.scrollBy(0, -500)",
                "bottom": "window.scrollTo(0, document.body.scrollHeight)",
                "top": "window.scrollTo(0, 0)",
            }
            js = scroll_map.get(direction, "window.scrollBy(0, 500)")
            await page.evaluate(js)  # type: ignore[attr-defined]

        elif step.step_type == StepType.WAIT:
            await page.wait_for_timeout(step.timeout_ms)  # type: ignore[attr-defined]

        elif step.step_type == StepType.SCREENSHOT:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            ss_path = str(Path(output_dir) / f"screenshot-{screenshot_count:03d}.png")
            await page.screenshot(path=ss_path, full_page=False, timeout=10000)  # type: ignore[attr-defined]
            logger.info(
                "Screenshot captured",
                extra={"path": ss_path, "desc": step.description},
            )
            return ss_path, ""

        elif step.step_type == StepType.ASSERT_TEXT:
            text_content = await page.text_content(step.selector, timeout=step.timeout_ms)  # type: ignore[attr-defined]
            if step.value not in (text_content or ""):
                return (
                    "",
                    f"Assert failed: expected '{step.value}' in '{text_content}'",
                )

        elif step.step_type == StepType.ASSERT_VISIBLE:
            visible = await page.is_visible(step.selector)  # type: ignore[attr-defined]
            if not visible:
                return "", f"Assert failed: '{step.selector}' is not visible"

    except Exception as exc:
        error_msg = f"Step {step.step_type.value} failed: {exc}"
        logger.warning(error_msg)
        return "", error_msg

    return "", ""


async def execute_interaction_plan(
    plan: InteractionPlan,
    output_dir: str = "/tmp/pr-videos/screenshots",
    viewport_width: int = 1280,
    viewport_height: int = 720,
) -> InteractionResult:
    """Execute a full interaction plan using Playwright.

    Returns an InteractionResult with screenshots, step count, and errors.
    """
    from playwright.async_api import async_playwright

    result = InteractionResult(total_steps=len(plan.steps))
    start_time = time.time()
    screenshot_count = 0

    logger.info(
        "Executing interaction plan",
        extra={"steps": len(plan.steps), "description": plan.description},
    )

    # Video recording directory (Playwright records each page as WebM)
    video_dir = str(Path(output_dir).parent / "video")
    Path(video_dir).mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            record_video_dir=video_dir,
            record_video_size={
                "width": viewport_width,
                "height": viewport_height,
            },
        )
        page = await context.new_page()

        for i, step in enumerate(plan.steps):
            logger.info(
                "Executing step",
                extra={
                    "step": i + 1,
                    "type": step.step_type.value,
                    "desc": step.description,
                },
            )
            ss_path, error = await _execute_step(page, step, output_dir, screenshot_count)

            if ss_path:
                result.screenshots.append(ss_path)
                screenshot_count += 1
            if error:
                result.errors.append(error)
            else:
                result.steps_completed += 1

        # Get the video path before closing (Playwright finalizes video on close)
        video = page.video
        if video:
            video_path_str = await video.path()
            result.video_path = str(video_path_str)
            logger.info("Video recorded", extra={"path": result.video_path})

        await context.close()
        await browser.close()

    result.duration_seconds = time.time() - start_time
    logger.info(
        "Interaction plan complete",
        extra={
            "completed": result.steps_completed,
            "total": result.total_steps,
            "screenshots": len(result.screenshots),
            "errors": len(result.errors),
        },
    )
    return result
