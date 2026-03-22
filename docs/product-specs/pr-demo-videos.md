# PRD: PR Demo Videos

## Problem

Code reviewers read diffs but never see the actual UI changes a PR introduces. This creates three problems:

1. **Slow reviews** — Reviewers must mentally simulate what the diff looks like rendered. For frontend changes, they often check out the branch locally just to see the result.
2. **Missed regressions** — Visual bugs (layout breaks, misaligned elements, missing content) are invisible in diffs. They slip through review and land in production.
3. **Poor context for stakeholders** — Product managers and designers can't easily see what shipped. They rely on screenshots pasted into PR descriptions (which are manual, often stale, and don't show interactions).

Cursor solved this for their cloud agents — every PR includes an auto-generated video walkthrough. We want the same capability as a standalone, open-source pipeline that works with any GitHub repo.

## Solution

When a PR is opened or updated on GitHub, a GitHub Actions workflow automatically:

1. Builds the frontend from the PR branch
2. Runs Playwright against it, recording the browser session as video
3. Generates TTS narration describing what changed (from the PR diff)
4. Assembles a final MP4 with narration + screen recording using FFmpeg
5. Posts the video as a PR comment (uploaded as a GitHub Actions artifact with a direct link)

The entire pipeline runs in CI. No external services required for the MVP (edge-tts is free, FFmpeg is free, Playwright is free).

## Users

- **Primary**: Developers opening PRs on repos with a frontend
- **Secondary**: Code reviewers, product managers, designers viewing PR comments

## Core Features

### F001: Health Endpoint (priority 1)
The backend API exposes GET /health returning `{"status": "healthy"}` with HTTP 200.

### F002: Structured Error Responses (priority 2)
All API error responses return JSON with a `correlation_id` field for tracing.

### F003: Structured JSON Logging (priority 3)
All application logging uses structured JSON format to stdout with timestamp, level, message, and correlation_id fields.

### F004: Playwright Recording of Target URL (priority 4)
Given a URL, the pipeline launches Playwright, navigates to the URL, performs a basic walkthrough (scroll, wait for load, capture interactions), and produces a WebM video file.

### F005: FFmpeg Video Assembly (priority 5)
The pipeline converts Playwright WebM output to MP4, trims dead frames, and produces a clean final video file suitable for embedding.

### F006: TTS Narration from PR Diff (priority 6)
Given a git diff, the pipeline uses an AI model to generate a narration script describing the visual changes, then synthesizes speech using edge-tts (free Microsoft neural voices). The audio track is mixed into the final MP4.

### F007: GitHub Actions Workflow (priority 7)
A reusable GitHub Actions workflow that triggers on `pull_request` events, runs the full pipeline, and posts the resulting video as a PR comment with a link to the artifact.

### F008: CLI Entry Point (priority 8)
A CLI command (`python -m pr_video generate --url <URL> --diff <path>`) that runs the full pipeline locally for testing and development.

## Architecture

```
backend/
  config/         → Environment variables, settings (leaf layer)
  models/         → Data structures, schemas (leaf layer)
  services/
    recorder.py   → Playwright browser recording
    assembler.py  → FFmpeg video assembly
    narrator.py   → Diff-to-narration + TTS
    pipeline.py   → Orchestrates recorder → narrator → assembler
  routers/
    health.py     → GET /health
    video.py      → POST /api/videos/generate (async trigger)
  db/             → (future: job storage)
  main.py         → FastAPI app entry point
  __main__.py     → CLI entry point
  tests/
    test_health.py
    test_recorder.py
    test_assembler.py
    test_narrator.py
    test_pipeline.py
```

### Module Dependency Rules

```
routers/    → may import: services/, models/, config/
services/   → may import: models/, config/
models/     → leaf layer (imports nothing from project)
config/     → leaf layer
```

### Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.12 | Playwright has first-class Python SDK, FFmpeg bindings available, fast prototyping |
| Framework | FastAPI | Async, typed, auto-docs, lightweight |
| Recording | Playwright (playwright-python) | Built-in video recording, headless Chrome |
| Video | FFmpeg (via subprocess) | Industry standard, handles all formats |
| TTS | edge-tts | Free Microsoft neural voices, no API key needed |
| Logging | Python logging + structlog | Structured JSON output, correlation IDs |
| Testing | pytest + pytest-asyncio | Standard Python testing |
| Lint/Format | ruff | Fast, replaces flake8 + black + isort |
| CI | GitHub Actions | Already configured in repo |

### Non-Goals (MVP)

- No web dashboard or UI
- No video hosting (use GitHub Actions artifacts)
- No real-time streaming
- No multi-repo support
- No authentication (runs in CI only)
- No database (stateless pipeline)

## Acceptance Criteria

1. `GET /health` returns HTTP 200 with `{"status": "healthy"}`
2. `python -m pr_video generate --url https://example.com` produces a valid MP4 file
3. The MP4 contains screen recording of the target URL
4. Given a diff file, the pipeline generates narrated audio and mixes it into the video
5. `scripts/validate.sh` exits 0 with all backend gates passing
6. A GitHub Actions workflow exists that can be triggered on PR events

## Dependencies (Ask First per AGENTS.md)

| Dependency | Purpose | License |
|------------|---------|---------|
| fastapi | Web framework | MIT |
| uvicorn | ASGI server | BSD |
| playwright | Browser automation + recording | Apache 2.0 |
| edge-tts | Text-to-speech (free) | MIT |
| structlog | Structured logging | MIT/Apache |
| ruff | Linting + formatting | MIT |
| pytest | Testing | MIT |
| pytest-asyncio | Async test support | Apache 2.0 |
| httpx | Async HTTP client (for tests) | BSD |

## Success Metrics

- Pipeline produces a video from URL in under 60 seconds
- validate.sh passes with 0 failures
- Scorecard grade remains A
- All features in feature_list.json verified end-to-end
