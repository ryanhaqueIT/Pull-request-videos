# Open Source Tools for Automated Demo Video Generation

## Programmatic Video Generation (Code-to-Video)

### Remotion (remotion.dev)
- **Approach**: React components rendered as video frames
- **Language**: TypeScript/React
- **Key Feature**: `useCurrentFrame()` + `interpolate()`, renders to MP4 via CLI
- **Server-side**: `@remotion/renderer` provides SSR APIs. Can render on Lambda via `@remotion/lambda`
- **Cost**: Most users render minutes of video for pennies on Lambda
- **Best for**: Scripted, branded product demos with animations
- **GitHub**: [remotion-dev/remotion](https://github.com/remotion-dev/remotion)

### Motion Canvas (motioncanvas.io)
- **Approach**: Generator functions for animation sequences
- **Language**: TypeScript
- **Key Feature**: Built-in Code component with syntax highlighting animation
- **Best for**: Code walkthrough videos, educational content
- **GitHub**: [motion-canvas/motion-canvas](https://github.com/motion-canvas/motion-canvas)

### Revideo (fork of Motion Canvas)
- **Approach**: Adds API layer and dynamic inputs to Motion Canvas
- **Key Feature**: Can deploy rendering on AWS Lambda
- **Best for**: Dynamic video generation at scale
- **GitHub**: [redotvideo/revideo](https://github.com/redotvideo/revideo)

### CodeVideo (codevideo.io)
- **Approach**: Event-sourced virtual IDE simulation
- **Architecture**: Virtual IDE with file explorer, editor, terminal, author, and mouse components
- **Export**: JSON actions → React component rendering → Puppeteer screenshot → FFmpeg MP4
- **Multi-format**: Same definition exports to MP4, Markdown, HTML, blog post
- **API**: Node Express API, send actions in JSON to get MP4/markdown/HTML links
- **Best for**: Software tutorial videos without real screen recording
- **GitHub**: [codevideo/codevideo-backend-engine](https://github.com/codevideo/codevideo-backend-engine)

## Terminal/CLI Recording

### VHS by Charmbracelet
- **Approach**: Declarative `.tape` scripts produce GIFs/MP4/WebM
- **CI-friendly**: Reproducible, deterministic recordings
- **Best for**: CLI tool demos, terminal-based workflows
- **GitHub**: [charmbracelet/vhs](https://github.com/charmbracelet/vhs)

### asciinema
- **Approach**: Records terminal as lightweight text-based recordings
- **Best for**: Embedding terminal sessions in docs
- **URL**: [asciinema.org](https://asciinema.org)

## Screen Recording with Auto-Polish

### Recordly (open source Screen Studio alternative)
- Auto-zoom on clicks, smooth cursor, device framing
- **GitHub**: [webadderall/Recordly](https://github.com/webadderall/Recordly)

### Screenize
- Auto-zoom, cursor effects, timeline editing
- macOS only
- **GitHub**: [syi0808/screenize](https://github.com/syi0808/screenize)

### screen-demo
- Lightweight zoom animations, cursor tracking
- Cross-platform
- **GitHub**: [njraladdin/screen-demo](https://github.com/njraladdin/screen-demo)

## Headless VM Recording (Cursor's Approach)

### Xvfb + ffmpeg x11grab
Standard approach for headless Linux screen recording:
```bash
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
ffmpeg -f x11grab -video_size 1920x1080 -i :99 \
  -codec:v libx264 -r 12 /tmp/output.mp4
```

### xvfb-record
Wrapper for Xvfb + ffmpeg recording
- **GitHub**: [grayleonard/xvfb-record](https://github.com/grayleonard/xvfb-record)

### puppeteer-screen-recorder
Chrome DevTools Protocol frame-by-frame capture with auto-managed FFmpeg
- **GitHub**: [prasanaworld/puppeteer-screen-recorder](https://github.com/prasanaworld/puppeteer-screen-recorder)

## AI-Assisted Pipelines

### Pagecast (MCP Server)
- Browser recording + AI interactions + GIF/video output
- Two-pass ffmpeg GIF: optimal 256-color palette + Bayer dithering
- Components: recorder.js (Playwright lifecycle), converter.js (ffmpeg conversion)

### Dev.to Pipeline (Javier Aguilar)
Complete AI-driven demo pipeline:
1. **Playwright** (`recordVideo`) — record browser interactions
2. **edge-tts** (free Microsoft neural voices) — generate narration
3. **ffmpeg** — assemble with variable speed segments
4. **Gemini 3.1 Pro** — QA sync check ("is audio synced with visuals?")

Result: 3:47 narrated demo in under 6 minutes, 14 scenes.

### ProductVideoCreator
AI Agent Skills toolkit for automated product video generation
- **GitHub**: [MatrixReligio/ProductVideoCreator](https://github.com/MatrixReligio/ProductVideoCreator)
- Uses Remotion + Playwright + edge-tts

## Managed Platforms

### E2B Desktop Sandbox
- Secure virtual desktop for AI agents
- WebRTC streaming, Python/JS SDK
- $0.05/hour per sandbox
- **GitHub**: [e2b-dev/desktop](https://github.com/e2b-dev/desktop)
- **Pricing**: [e2b.dev/pricing](https://e2b.dev/pricing)

### Mux (Video Delivery)
- Adaptive bitrate streaming
- Upload API, playback URLs
- $0.00395/min encoded + $0.00035/min streamed
- **URL**: [mux.com](https://mux.com)

### Arcade (Interactive Demos)
- Chrome extension captures clicks/scrolls
- Produces interactive embeddable walkthroughs (not video)
- **URL**: [arcade.software](https://arcade.software)
