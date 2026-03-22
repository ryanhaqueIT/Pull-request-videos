# ExecPlan: PR Demo Videos Pipeline


## Purpose / Big Picture


When a developer opens a pull request on a GitHub repo, the system automatically generates a narrated video walkthrough showing what the PR changes look like in the browser. The video is posted as a PR comment. Reviewers can watch the video instead of mentally simulating what the diff looks like rendered.

To demonstrate it works: run `python -m pr_video generate --url https://example.com` and get back a valid MP4 file with screen recording and TTS narration.


## Context and Orientation


This is a greenfield Python backend in the `Pull-request-videos` repository. There is no existing application code — only harness engineering scripts (validate.sh, check_imports.py, etc.) and documentation.

The backend will live in `backend/` and use FastAPI. The core pipeline has three stages:
1. **Record** — Playwright opens a URL in headless Chrome and records the browser session as WebM
2. **Narrate** — An AI model reads a git diff and generates a narration script; edge-tts converts it to audio
3. **Assemble** — FFmpeg combines the screen recording with the narration audio into a final MP4

Key files that will be created:
- `backend/main.py` — FastAPI application entry point
- `backend/__main__.py` — CLI entry point (`python -m pr_video`)
- `backend/config/settings.py` — Environment variable loading
- `backend/models/video.py` — Pydantic schemas
- `backend/routers/health.py` — GET /health
- `backend/routers/video.py` — POST /api/videos/generate
- `backend/services/recorder.py` — Playwright recording
- `backend/services/narrator.py` — Diff-to-narration + TTS
- `backend/services/assembler.py` — FFmpeg video assembly
- `backend/services/pipeline.py` — Orchestrates the full flow
- `backend/tests/` — All test files


## Plan of Work


### Milestone 1: Backend Scaffold with Health Endpoint

Create the backend/ directory structure with FastAPI, a working health endpoint, structured logging with correlation IDs, and configuration management. After this milestone, `GET /health` returns HTTP 200, all backend validation gates pass (B1-B7), and `scripts/validate.sh` exits 0 for backend gates.

Verify: `cd backend && python -m pytest tests/ -v` passes. `curl http://localhost:8000/health` returns `{"status":"healthy"}`.


### Milestone 2: Video Recording Service

Build the Playwright-based screen recorder that takes a URL and produces a WebM video file. After this milestone, `python -c "from services.recorder import record_url; ..."` can record any URL to a video file.

Verify: `cd backend && python -m pytest tests/test_recorder.py -v` passes. Output WebM file exists and is >0 bytes.


### Milestone 3: Narration Service

Build the narration pipeline: diff → AI narration script → edge-tts audio. After this milestone, given a diff string, the system produces an MP3 audio file with spoken narration.

Verify: `cd backend && python -m pytest tests/test_narrator.py -v` passes. Output MP3 file exists.


### Milestone 4: Assembly Service + CLI

Build the FFmpeg assembler that combines video + audio into final MP4. Wire up the full pipeline through a CLI entry point.

Verify: `python -m pr_video generate --url https://example.com` produces a valid MP4 file. `scripts/validate.sh` exits 0.


## Concrete Steps

### Milestone 1

    $ cd backend
    $ python -m pytest tests/ -v --tb=short
    tests/test_health.py::test_health_returns_200 ... PASSED
    tests/test_health.py::test_health_response_format ... PASSED

    $ curl http://localhost:8000/health
    {"status":"healthy"}

    $ cd .. && bash scripts/validate.sh
    # B1-B6 should pass, B7/B8 skip (no type checker / mutmut installed)

### Milestone 2

    $ cd backend && python -m pytest tests/test_recorder.py -v
    tests/test_recorder.py::test_record_url_produces_video ... PASSED

### Milestone 3

    $ cd backend && python -m pytest tests/test_narrator.py -v
    tests/test_narrator.py::test_generate_narration_script ... PASSED
    tests/test_narrator.py::test_synthesize_speech ... PASSED

### Milestone 4

    $ python -m pr_video generate --url https://example.com --output demo.mp4
    Recording https://example.com ...
    Generating narration ...
    Assembling final video ...
    Output: demo.mp4 (1.2 MB, 15 seconds)


## Validation and Acceptance


1. `GET http://localhost:8000/health` returns HTTP 200 with `{"status": "healthy"}`
2. `python -m pr_video generate --url https://example.com` produces a file `demo.mp4` that is a valid MP4 video
3. All backend tests pass: `cd backend && python -m pytest tests/ -v` shows 0 failures
4. `scripts/validate.sh` exits 0 with all backend gates (B1-B6) passing
5. Structured JSON log lines appear on stdout when the server runs


## Idempotence and Recovery


Every step creates files from scratch. No database, no state. Re-running any milestone overwrites previous output safely. If Playwright fails to install, run `playwright install chromium`. If FFmpeg is not found, install it via system package manager. All temporary video files are written to `/tmp/` or a configurable output directory.

---

## Progress

- [x] (2026-03-22T12:45Z) Milestone 1: Backend scaffold — FastAPI app, health endpoint, structured logging, config module, 4 health tests passing
- [x] (2026-03-22T12:50Z) Milestone 2: Video recording service — Playwright recorder with scroll walkthrough, test with mocked browser
- [x] (2026-03-22T12:52Z) Milestone 3: Narration service — diff parser, edge-tts synthesis, Hypothesis property test
- [x] (2026-03-22T12:55Z) Milestone 4: Assembly service + CLI — FFmpeg assembler with imageio-ffmpeg fallback, CLI entry point, pipeline orchestrator
- [x] (2026-03-22T13:00Z) All 15 unit tests passing, B1-B6 gates passing, scorecard A+ (30/31)
- [x] (2026-03-22T13:03Z) Live verification F001: GET /health → 200 {"status":"healthy"}
- [x] (2026-03-22T13:03Z) Live verification F002: GET /nonexistent → 404 with correlation_id
- [x] (2026-03-22T13:03Z) Live verification F003: Structured JSON logging confirmed on stdout
- [x] (2026-03-22T13:04Z) Live verification F004: Playwright recorded example.com → 34KB WebM
- [x] (2026-03-22T13:04Z) Live verification F005: FFmpeg converted WebM → 15.9KB MP4
- [x] (2026-03-22T13:04Z) Live verification F006: Narration from diff → 79KB MP3 audio
- [x] (2026-03-22T13:05Z) Live verification F007: Full CLI pipeline → 82KB MP4 with recording + narration + assembly
- [x] (2026-03-22T13:06Z) Live verification F008: pr-video.yml workflow verified
- [x] (2026-03-22T13:07Z) Final: ExecPlan updated, feature list 8/8, validate.sh run

## Surprises & Discoveries

- FFmpeg is not available on the Windows system PATH. Used `imageio-ffmpeg` pip package as fallback which bundles a portable ffmpeg binary. Added `_find_ffmpeg()` helper to assembler.py.
- `python -m pr_video` doesn't work because the backend/ directory isn't a proper Python package with that name. CLI invocation is `cd backend && python __main__.py generate ...` instead. Updated workflow and docs.

## Decision Log

- (2026-03-22) Using Python + FastAPI — Playwright has first-class Python SDK, edge-tts is Python, and FFmpeg subprocess calls are trivial. See docs/research/03-effort-estimation.md.
- (2026-03-22) Tier 1 approach (Playwright + TTS + FFmpeg) — cheapest, simplest, no external API keys needed for MVP. Upgrade to Tier 2 (Mux pipeline) later if needed.
- (2026-03-22) edge-tts over ElevenLabs — free, no API key, good enough for MVP. ElevenLabs has better quality but costs money.

## Outcomes & Retrospective

All 8 features verified end-to-end. The pipeline records a real URL (example.com), generates narration from a real diff, synthesizes speech, and assembles a final MP4. Total pipeline time: ~11 seconds for a simple page.

Key takeaway: live verification caught two bugs that unit tests missed — FFmpeg not on PATH (fixed with imageio-ffmpeg fallback) and wrong CLI module name (fixed by updating invocation pattern).
