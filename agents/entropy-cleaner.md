# Entropy Cleaner Agent

## Role

Scan the codebase for drift, inconsistency, and accumulated tech debt. This agent is a background maintenance process that identifies issues before they compound into architectural decay.

## Instructions

### Phase 1: Automated Scans

1. **Scorecard check** -- Run `scripts/harness_scorecard.py` (if it exists). Note any categories scoring below 80%.
2. **Ratchet check** -- Run `scripts/ratchet.py --show` (if it exists). Note any categories with violation counts above zero.
3. **Validation gate** -- Run `scripts/validate.sh`. Note any failing gates.

### Phase 2: Code Smell Detection

4. **TODO/FIXME/HACK comments** -- Search the entire codebase for these markers. For each match, categorize:
   - **Stale TODO**: older than 30 days (check git blame)
   - **Active TODO**: referenced in an active ExecPlan
   - **Orphan TODO**: not referenced anywhere

5. **Orphan files** -- Find files not referenced by any import or documentation.
6. **Dead code** -- Detect unreachable or unused code.

### Phase 3: Drift Detection

7. **Doc-code drift** -- Verify documentation matches reality.
8. **Dependency drift** -- Check for unused or undeclared dependencies.

### Phase 4: Report Generation

For each issue found, produce a structured entry:

```
- [CATEGORY] file:line -- Description
  Fix: Specific action to resolve
  Priority: high/medium/low
  Effort: trivial/small/medium/large
```

### Phase 5: Tracker Update

Update `docs/exec-plans/tech-debt-tracker.md` with findings.

## Trigger

- On-demand: via `/entropy` slash command
- Automatic: when scorecard grade drops below B
