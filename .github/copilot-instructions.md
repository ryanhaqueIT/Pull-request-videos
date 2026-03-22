# Pull Request Videos — Copilot Instructions

> Keep in sync with AGENTS.md and CLAUDE.md.

## THE RULE

**`./scripts/validate.sh` must exit 0 before every commit. No exceptions.**

## Commands

```bash
./scripts/validate.sh              # Gate — run before every commit
./scripts/boot_worktree.sh         # Boot locally (dynamic ports)
```

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

## Golden Principles

1. No secrets in code — use secret managers or env vars.
2. Structured logging only — `logger.info()` with correlation_id. Never `print()`.
3. Module boundaries — enforced import DAG above.
4. No God files — files exceeding 300 lines must be split.
5. Type hints on all public functions.
6. No bare except clauses — must specify exception type.

## Boundaries

### Always
- Run `scripts/validate.sh` before committing
- Fix lint and format errors
- Write tests for new code
- Use structured logging

### Ask First
- Adding new dependencies
- Changing public API contracts
- Modifying database schemas
- Changing auth logic
- Modifying CI workflows

### Never
- Delete existing tests
- Skip validate.sh
- Commit secrets or credentials
- Push directly to main/master
- Disable linters or type checkers
- Put business logic in routers/controllers

## Git

Branch: `feature/<desc>`, `fix/<desc>`, `chore/<desc>`
Commit: `feat(scope):`, `fix(scope):`, `docs(scope):`, `chore(scope):`
