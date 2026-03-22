# Pull Request Videos

> Keep in sync with AGENTS.md and .github/copilot-instructions.md.

## THE RULE

**`./scripts/validate.sh` must exit 0 before every commit. No exceptions.**

Applies to all agents, subagents, humans, hotfixes, and "quick changes."
validate.sh auto-detects backend, frontend, and infrastructure. If it misses
something, fix validate.sh — not this file.

## Commands

```bash
./scripts/validate.sh              # Gate — run before every commit
./scripts/boot_worktree.sh         # Boot locally (dynamic ports)
./scripts/boot_worktree.sh --stop  # Stop local instances
./scripts/boot_worktree.sh --check # Health check running instances

# Backend (once language is chosen):
# cd backend && ruff check .         # Lint (Python)
# cd backend && ruff format .        # Format (Python)
# cd backend && python -m pytest tests/ -v  # Test (Python)
# cd backend && npx eslint .         # Lint (Node.js)
# cd backend && npx prettier --check . # Format (Node.js)
# cd backend && npm test             # Test (Node.js)

# Frontend (once created):
# cd frontend && npx tsc --noEmit    # Type check
# cd frontend && npx eslint .        # Lint
# cd frontend && npm run build       # Build
```

<!-- EVOLVE: Update commands once stack is chosen and initial features land -->

## Module Dependency Rules

```
No modules defined yet — this is a greenfield project.

Prescribed architecture (adapt when code lands):
  routers/    → may import: services/, models/, auth/
  services/   → may import: db/, models/
  db/         → may import: models/
  models/     → leaf layer (imports nothing from project)
  auth/       → may import: db/, models/
  config/     → leaf layer
```

Enforced by `scripts/check_imports.py` in CI. Violations fail the build.

## Golden Principles (mechanically enforced)

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

## Testing Requirements

Tests must prove the code works, not just that it runs.

- **Every new source file** in a testable module (services/, db/) gets a corresponding test file
- **Property-based tests required** for all pure functions (Hypothesis for Python, fast-check for TS)
- **Behavior tests, not implementation tests**
- **Mutation testing** via mutmut (Python) or Stryker (TS). Gate B8 in validate.sh
- **3-mock maximum**. If a test needs >3 mocks, the code is too coupled

## Context Health

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

## Execution Limits

- Same fix attempted more than **3 times** → STOP and escalate
- validate.sh failed **5+ times** consecutively → STOP and explain
- Failing external API calls → max **2 retries**
- More than **3 alternative approaches** → ask user for direction
- Single file edit exceeds **100 lines** → pause and confirm approach

## Throughput Philosophy

Ship fast. Fix forward. Prefer boring technology. One concern per PR.

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

1. **Module added** → Update Module Dependency Rules section above
2. **Command added** → Update Commands section above + all synced agent files
3. **Agent makes a mistake** → Add a boundary rule to Boundaries section
4. **Architectural decision** → Create a decision doc in `docs/design-docs/`
5. **Session start** → Quick drift check: modules match reality, commands still work

## ExecPlans

Complex tasks (>30 min, multi-file, design decisions) require an ExecPlan.
See `PLANS.md` for the format. Active plans live in `docs/exec-plans/active/`.

## Git

Branch: `feature/<desc>`, `fix/<desc>`, `chore/<desc>`
Commit: `feat(scope):`, `fix(scope):`, `docs(scope):`, `chore(scope):`
PR: one concern per PR. `validate.sh` must pass first.
