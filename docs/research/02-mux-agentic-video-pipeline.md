# Mux Agentic Screen Recording Pipeline

## Overview

Mux published a detailed engineering blog post (Jan 28, 2026) describing a 3-phase pipeline for generating narrated screen recordings using AI agents. This mirrors Hollywood filmmaking: pre-production, performance, post-production.

## Architecture: Three-Phase Pipeline

### Phase 1: Pre-Production

1. **Accessibility Snapshots**: Uses [Vercel agent-browser](https://github.com/vercel-labs/agent-browser) to visit each page and capture semantic structure with element refs (`@e1`, `@e5`, etc.)
2. **AI Narration**: Snapshots feed Claude API with a persona prompt, requesting structured narration with scroll targets (JSON schema output guarantees valid segments with "text" and "scrollTo" fields)
3. **Speech Synthesis**: Narration routes to **ElevenLabs' with-timestamps endpoint**, returning audio plus **character-level timing alignment** data (millisecond-precise timestamps per character)

### Phase 2: Performance (Recording)

1. Fresh browser instance launches with video recording enabled
2. **Content-aware scrolling** synchronized to narration timing
3. When Claude mentions specific page sections, browser smoothly scrolls to bring elements into view
4. Scrolling uses `document.documentElement.style.scrollBehavior = 'smooth'` + `scrollIntoView` for element refs

### Phase 3: Post-Production

FFmpeg handles final assembly:
- **Extraction**: `-ss` (start) + `-t` (duration) flags for precise time windows
- **Concatenation**: `concat demuxer` joins segments at container level (no re-encoding)
- **Audio mixing**: `adelay` filter positions narration clips with millisecond precision
- **Final merge**: Combines concatenated video with positioned audio tracks
- **Upload**: Finished MP4 uploads to Mux API for adaptive bitrate streaming

## Key Innovation

Character-level timing alignment eliminates "timing drift" — narration and scrolling sync perfectly because both derive from identical ElevenLabs timing data.

## MCP Server

Exposes a single tool: `create_narrated_recording` accepting persona string and URL array, orchestrating the entire autonomous workflow.

## Required Services

| Service | Role | Cost |
|---------|------|------|
| Vercel agent-browser | Browser automation + recording | Free (OSS) |
| Claude API | Narration generation | ~$0.50-2 per video |
| ElevenLabs | Speech with timestamps | ~$0.30/min speech |
| Mux | Hosting + streaming | $0.00395/min encoded |

## Sources

- [Mux Blog: Agentic Screen Recording](https://www.mux.com/blog/agentic-video-screen-recording)
- [Vercel agent-browser](https://github.com/vercel-labs/agent-browser)
