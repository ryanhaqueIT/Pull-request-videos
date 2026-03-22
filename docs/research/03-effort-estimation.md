# Effort Estimation: Replicating Cursor's Auto Demo Videos

## Four Tiers of Approach

### Tier 1: Playwright + TTS + FFmpeg (3-5 days, ~$0/month)

The simplest approach. Based on the [dev.to article](https://dev.to/javieraguilarai/i-made-a-product-demo-video-entirely-with-ai-e6h).

| Component | Tool | Role |
|-----------|------|------|
| Browser automation | Playwright (`recordVideo: {dir: 'videos/'}`) | Records browser at viewport resolution |
| Narration | edge-tts (free Microsoft neural voices) | Generates voiceover per scene |
| Assembly | ffmpeg | Concatenates segments, adds audio, variable speed |
| QA | Gemini | Upload video → "is audio synced?" → timestamped report |

**Result**: 3-minute narrated demo with 14 scenes, variable speed, subtitles.
**Limitations**: Browser-only. No terminal/desktop. Looks "automated."

### Tier 2: Mux Agentic Pipeline (1-2 weeks, ~$50-100/month)

The Mux blog approach with intelligent narration.

- Claude generates structured narration with scroll targets
- ElevenLabs produces speech with character-level timing
- Content-aware scrolling syncs perfectly with voiceover
- FFmpeg assembles with millisecond-precision audio positioning

**Cost per video**: ~$1-3
**Result**: Professional narrated walkthroughs with synced scrolling.

### Tier 3: E2B Desktop + Xvfb + FFmpeg (2-4 weeks, ~$100-300/month)

Full desktop recording — replicates Cursor's core capability.

**Option A: E2B Desktop Sandbox (managed)**
```python
from e2b_desktop import Desktop
desktop = Desktop()
desktop.stream.start()  # WebRTC streaming
desktop.launch('google-chrome')
desktop.left_click(500, 300)
desktop.write("hello world")
```
- $0.05/hour per sandbox
- Python/JS SDK, no infra to manage
- Gap: No built-in MP4 recording — need Xvfb+ffmpeg inside sandbox

**Option B: DIY Docker + Xvfb + FFmpeg**
```bash
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
ffmpeg -f x11grab -video_size 1920x1080 -i :99 -codec:v libx264 -r 12 /tmp/output.mp4 &
# Run your agent...
```
- Just Docker/EC2 compute (~$0.05-0.10/hour for t3.medium)
- Known issue: resolution >1024x768 can distort in containers

### Tier 4: Firecracker + VNC + Production Pipeline (2-6 months, $10K+/month)

What Cursor actually built. Requires:
- Custom Rust VM orchestrator (Anyrun equivalent)
- Firecracker microVM management
- VNC recording pipeline
- Mux video delivery
- Onboarding automation (repo detection, secrets, dependencies)
- Agent parallelization (Best-of-N, subagents)

## Comparison Matrix

| Approach | Build Time | Monthly Cost | Quality | Desktop? | Narration? |
|----------|-----------|-------------|---------|----------|------------|
| Playwright + TTS + FFmpeg | 3-5 days | ~$0 | Basic | No | Yes |
| Mux Agentic Pipeline | 1-2 weeks | ~$50-100 | Polished | No | Yes (synced) |
| E2B + Xvfb + FFmpeg | 2-4 weeks | ~$100-300 | Good | Yes | DIY |
| DIY Docker + Xvfb | 1-2 weeks | ~$50 | Good | Yes | DIY |
| Firecracker + VNC (Cursor) | 2-6 months | $10K+ | Production | Yes | Yes |

## Recommendation for WeddingOS

Start with **Tier 1** (Playwright recording of existing E2E tests → GIF for README). This is already partially built — the AWS-Hackathon repo has 8 Playwright journey specs with screenshot milestones. Adding `video: "on"` and a ffmpeg GIF converter is a few hours of work.

Upgrade to **Tier 2** when you need polished DevPost submission videos.
