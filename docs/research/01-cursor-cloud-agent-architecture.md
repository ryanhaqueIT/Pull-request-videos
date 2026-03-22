# Cursor Cloud Agent — Video Recording Architecture

## Overview

Cursor launched Cloud Agents with Computer Use on February 24, 2026. Each agent runs in an isolated Linux VM, does real coding work, records itself, and produces a merge-ready PR with video artifacts attached.

## VM Infrastructure

- **AWS Firecracker** microVMs: 125ms boot, ~5MB memory overhead
- **Anyrun**: Cursor's custom Rust orchestrator for VM lifecycle management
- Persistent memory snapshots — can hibernate/rehydrate VMs preserving full state (open browsers, running servers)
- VM size tiers planned (S/M/L/XL)

## Remote Access: VNC

Jonas (Cursor cofounder, ex-Autotab) on Latent Space podcast:

> "We unshift [the browser iframe] because we felt that the remote desktop was sufficiently low latency and more general purpose."

They replaced an initial browser-iframe approach with **full VNC remote desktop** because:
- More general-purpose (supports terminal, file manager, any app — not just browser)
- Lower complexity than maintaining browser-specific integrations
- Acceptable latency for the use case

## Computer Use: Pixels-In, Coordinates-Out

The agent operates on pure visual I/O:
- Model receives screen pixels as input
- Outputs box coordinates and click/type actions
- Works with Claude Opus 4.5, Sonnet 5.3+

Jonas: *"round about Sonnet 4 fire is when this started being good enough to just automate fully by pixel."*

## Video Recording Pipeline

Three-pillar output:

1. **Testing**: Agent runs code, executes tests E2E before returning PRs
2. **Video**: Captures agent session with chapters/segments, auto panning/zooming to highlight relevant areas
3. **Remote Control**: Live VNC access for debugging

Video delivery confirmed via **Mux** (playback IDs found in `cursor.com/changelog` source code). Cursor-branded wallpaper and TikTok-style watermarks added automatically.

## Likely Recording Stack (not publicly confirmed)

Based on VNC confirmation and standard Linux patterns:
- **Xvfb** (X Virtual Framebuffer) for headless display
- **ffmpeg x11grab** or VNC recorder for framebuffer-to-video capture
- **Mux** for upload, encoding, adaptive bitrate streaming

## Agent Parallelization

- **Best-of-N**: 5+ agents on identical tasks in isolated VMs
- **Subagent hierarchy**: Smart model routing (Sonnet for exploration, Opus for synthesis)
- **Grind mode**: 3-day agent runs with upfront planning validation
- ~30-35% of Cursor's own merged PRs are now agent-created

## Key Engineering Tradeoffs

- Onboarding is hard: *"we spent an inordinate amount of time on cursor.com/onboard"* — repo detection, secret management, dependency installation
- Memory/context management across long sessions remains a friction point
- Token economics scale dramatically with parallelization

## Sources

- [Latent Space: Cursor's Third Era](https://www.latent.space/p/cursor-third-era)
- [Cursor Changelog 02-24-26](https://cursor.com/changelog/02-24-26)
- [Sam Whitmore meta-demo tweet](https://x.com/sjwhitmore/status/2026427802623553660)
- [NxCode: Cursor Cloud Agents Guide](https://www.nxcode.io/resources/news/cursor-cloud-agents-virtual-machines-autonomous-coding-guide-2026)
- [Cloud VMs for Autonomous Agents](https://alexlavaee.me/blog/cloud-vms-autonomous-agent-infrastructure/)
