# Pull Request Videos

## THE RULE

**`./scripts/validate.sh` must exit 0 before every commit. No exceptions.**

Applies to all agents, subagents, humans, hotfixes, and "quick changes."
validate.sh auto-detects backend, frontend, and infrastructure. If it misses
something, fix validate.sh — not this file.

## Authority Hierarchy

**This file (AGENTS.md) is the governing authority for this repository.**

When ANY other instruction source conflicts — skills, slash commands,
superpowers, CLAUDE.md, or external documentation — THIS FILE WINS.

- Plans go in `docs/exec-plans/active/`, not wherever a skill suggests
- Specs go in `docs/product-specs/`, not wherever a skill suggests
- validate.sh must pass before commit, regardless of what any skill says
- Feature verification is required, regardless of what any skill says

Enforced mechanically: hooks block writes to wrong locations and block
commits when validate.sh fails.

## Evidence Over Claims

You may NOT say "done", "complete", "implemented", or "finished" without
showing command output that proves it. Specifically:

- For API features: show the curl command and its response
- For UI features: show a Playwright assertion or screenshot result
- For CLI features: show the command and its output
- For tests: show the test runner output with pass/fail counts

"I created the file" is NOT evidence. "curl returned 200 with expected body" IS.
A Stop hook enforces this: you cannot stop until all features in
`.harness/feature_list.json` are verified.

## Commands

```bash
./scripts/validate.sh              # Gate — run before every commit
./scripts/boot_worktree.sh         # Boot locally (dynamic ports)
./scripts/boot_worktree.sh --stop  # Stop local instances
./scripts/boot_worktree.sh --check # Health check running instances

# Backend (Python / FastAPI):
cd backend && ruff check .                    # Lint
cd backend && ruff format .                   # Format
cd backend && python -m pytest tests/ -v      # Test
cd backend && uvicorn main:app --reload       # Run dev server

# CLI:
cd backend && python __main__.py generate --url <URL> --output demo.mp4

# Agent (AI-powered demo):
cd backend && python __main__.py agent --url <URL> --diff <DIFF_FILE>  # Run agent locally
docker compose -f docker-compose.agent.yml up control-plane            # Start control plane
docker compose -f docker-compose.agent.yml --profile agent run agent   # Run agent in sandbox
```

## Module Dependency Rules

```
backend/
  routers/         → may import: services/, models/, config/
    health.py        GET /health
    video.py         POST /api/videos/generate
    agent.py         POST /api/agents/run
    control.py       POST /api/control/sessions, /llm, /artifacts
  services/        → may import: models/, config/
    pipeline.py      Orchestrates recorder → narrator → assembler
    recorder.py      Playwright browser recording
    narrator.py      Diff → narration script → edge-tts audio
    assembler.py     FFmpeg video + audio assembly
    gateway.py       Gateway protocol (DirectGateway / ControlPlaneGateway)
    agent_brain.py   Claude-powered reasoning loop (plan → execute → summarize)
    interaction.py   Playwright browser interactions (click, type, screenshot)
    screen_capture.py  Xvfb + ffmpeg desktop recording
    artifact.py      Collect videos, screenshots, logs into bundle
    github_pr.py     Format and post PR comments with artifacts
    sandbox.py       Docker container lifecycle management
    control_plane.py Session management, LLM proxy, artifact storage
  models/          → leaf layer (imports nothing from project)
    video.py         VideoRequest, VideoResult, VideoStatus
    agent.py         AgentSession, InteractionPlan, InteractionStep
    artifact.py      Artifact, ArtifactBundle
  config/          → leaf layer (only module that reads os.environ)
sandbox/           → standalone (runs inside Docker container)
  Dockerfile         Agent sandbox image
  entrypoint.sh      Start Xvfb + ffmpeg + agent
  agent_runner.py    Sandbox entry point
```

Enforced by `scripts/check_imports.py` in CI. Violations fail the build.

## Golden Principles (mechanically enforced)

Violations are caught by validate.sh. These are not suggestions.

1. **No secrets in code** — use secret managers or env vars.
2. **Structured logging only** — `logger.info()` with correlation_id. Never `print()`.
3. **Module boundaries** — enforced import DAG above.
4. **No God files** — `scripts/check_architecture.py` flags files exceeding 300 lines.
5. **Type hints on all public functions** — enforced by `scripts/check_golden_principles.py`.
6. **No bare except clauses** — must specify exception type.
7. **Mutation-tested code** — tests must catch bugs, not just execute lines. Gate B8 in validate.sh.

## Boundaries

### Always (do without asking)
- Run `scripts/validate.sh` before committing
- Fix lint and format errors
- Update AGENTS.md when adding modules or commands
- Write tests for new code
- Use structured logging (no print/console.log)
- Follow the module dependency rules

### Ask First (propose and wait for approval)
- Adding new dependencies
- Changing public API contracts
- Modifying database schemas or migrations
- Changing authentication/authorization logic
- Modifying CI workflows
- Adding new top-level modules
- Changing infrastructure configuration

### Never (absolute prohibition)
- Delete existing tests
- Skip validate.sh or bypass pre-commit hooks
- Commit secrets, API keys, or credentials
- Push directly to main/master
- Disable linters or type checkers
- Put business logic in routers/controllers
- Import database libraries outside the data access layer
- Use `print()`/`console.log()` in production code

<!-- EVOLVE: Tighten "Ask" boundary tier as conventions solidify -->

## Testing Requirements

Tests must prove the code works, not just that it runs.

- **Every new source file** in a testable module (services/, db/) gets a corresponding test file
- **Property-based tests required** for all pure functions. Use Hypothesis (Python) or fast-check (TS). Properties are derived from the spec, not from the implementation. Example: `sort(sort(x)) == sort(x)`, "this function always returns a positive number"
- **Behavior tests, not implementation tests**. Good: "POST /api/videos returns 201 with a video_id field." Bad: "RecorderService._init_browser calls playwright.launch 1 time"
- **Mutation testing** via mutmut (Python) or Stryker (TS). Gate B8 in validate.sh. Tests that don't catch injected mutations are tests that don't catch real bugs
- **3-mock maximum**. If a test needs >3 mocks, the code is too coupled. Refactor the code, don't add more mocks

## Context Health

Long sessions degrade performance. Microsoft Research measured 39% performance drop in multi-turn conversations.

**If you hit 5+ consecutive errors on the same issue:**
1. STOP attempting fixes
2. Re-read AGENTS.md completely
3. Re-read the relevant exec plan
4. Summarize what you've tried and what failed
5. Try a fundamentally different approach

**If validate.sh has failed 5+ times consecutively:**
1. STOP running validate.sh
2. Read every failure message carefully
3. Fix failures one at a time, starting with the simplest
4. Only re-run validate.sh after making a concrete change

**If you notice yourself generating similar output repeatedly:** you are in a repetition loop. Stop, summarize the situation to the user, and ask for direction.

## Execution Limits

Runaway loops waste tokens and time. These limits are hard stops.

- If you have attempted the **same fix more than 3 times**, STOP and escalate to the user
- If **validate.sh has failed 5+ times consecutively**, STOP and explain what's blocking
- Do not retry failing external API calls more than **twice**
- Do not generate more than **3 alternative approaches** without user input on direction
- If a single file edit exceeds **100 lines of changes**, pause and confirm approach with the user

## Throughput Philosophy

Ship fast. Fix forward. A small bug that ships and gets fixed in 30 minutes is better than a perfect PR that blocks for 3 hours of review.

- **Prefer boring technology** — choose well-understood tools over clever new ones
- **One concern per PR** — small PRs merge fast, large PRs rot
- **Recurring cleanup** — schedule entropy scans weekly, not after each commit
- **Scope enforcement** — if a task grows beyond the original plan, create a new plan for the overflow rather than expanding the current one

## Progressive Disclosure

| File | When to read |
|------|-------------|
| `docs/exec-plans/active/*.md` | Before implementing any task |
| `docs/product-specs/*.md` | Before building a feature |
| `docs/design-docs/*.md` | Before reopening a decision (ACCEPTED = locked) |
| `docs/QUALITY_SCORE.md` | When reviewing code |
| `docs/SECURITY.md` | When handling auth or secrets |
| `docs/RELIABILITY.md` | When handling errors, logging, retries |
| `docs/references/*.txt` | When using external APIs |

## Feature List

Features are tracked in `.harness/feature_list.json`. Each feature has `passes: true/false`.
- You may ONLY set `passes: true` after verifying the feature works end-to-end.
- You may NEVER remove features, edit descriptions, or change steps.
- Run `/features` to see current status.

## Standing Maintenance Orders

These trigger automatically during normal work:
1. **Module added** → Update Module Dependency Rules section above
2. **Command added** → Update Commands section above + all synced agent files
3. **Agent makes a mistake** → Add a boundary rule to Boundaries section to prevent recurrence
4. **Architectural decision** → Create a decision doc in `docs/design-docs/`
5. **Session start** → Quick drift check: modules match reality, commands still work

## ExecPlans

Complex tasks (>30 min, multi-file, design decisions) require an ExecPlan.
See `PLANS.md` for the format. Active plans live in `docs/exec-plans/active/`.

## Git

Branch: `feature/<desc>`, `fix/<desc>`, `chore/<desc>`
Commit: `feat(scope):`, `fix(scope):`, `docs(scope):`, `chore(scope):`
PR: one concern per PR. `validate.sh` must pass first.
