# Pull Request Videos — Research & Documentation

This folder contains all research, discussions, and technical documentation from our deep investigation into automated demo video generation.

## Research Documents

| Doc | Topic |
|-----|-------|
| [01 - Cursor Cloud Agent Architecture](research/01-cursor-cloud-agent-architecture.md) | How Cursor's cloud agents record demo videos (Firecracker VMs, VNC, Mux, computer use) |
| [02 - Mux Agentic Video Pipeline](research/02-mux-agentic-video-pipeline.md) | Mux's 3-phase filmmaking pipeline (pre-production, performance, post-production) with Claude + ElevenLabs + FFmpeg |
| [03 - Effort Estimation](research/03-effort-estimation.md) | 4-tier analysis: from 3-day Playwright hack to 6-month Cursor-scale infrastructure |
| [04 - Open Source Tools](research/04-open-source-tools.md) | Comprehensive catalog: Remotion, Motion Canvas, CodeVideo, VHS, E2B, Pagecast, and more |
| [05 - Google Calendar Investigation](research/05-google-calendar-availability-investigation.md) | CloudWatch log analysis of WeddingOS calendar availability — what's working, what's broken |
| [06 - Existing Playwright Tests](research/06-existing-playwright-tests.md) | Inventory of AWS-Hackathon's 8 E2E journey specs + recording config |
| [07 - GCP Calendar Service](research/07-gcp-hackathon-calendar-service.md) | Code analysis of GCP-Hackathon's calendar integration vs AWS-Hackathon |

## Key Findings

1. **Cursor records real VM sessions** — not scripted animations. Agent works in Firecracker VM with VNC, records the framebuffer, delivers via Mux.

2. **The simplest replication is Playwright + FFmpeg** — our AWS-Hackathon already has 8 Playwright E2E journeys. Adding `video: "on"` + GIF conversion is hours of work.

3. **Google Calendar availability checking has never worked in a real Connect voice call** — the test vendor has no OAuth token. The bridge Lambda had cryptography library issues. Only 1 successful GCal API call out of ~6 attempts.

4. **14 vendors have valid OAuth tokens** in DynamoDB but none are connected to the Amazon Connect test vendor ID.

## Quick Start

```bash
# Record E2E tests as video
cd /c/Users/drnaz/Ryan/AWS-Hackathon/tests/e2e
npx playwright test --config=playwright.record.config.ts

# Convert to GIF for README
node scripts/convert-videos.mjs demo-recordings demo-gifs
```
