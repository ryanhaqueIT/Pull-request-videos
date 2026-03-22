#!/usr/bin/env python3
"""check_imports.py — Enforce module dependency boundaries.

Scans Python files in backend/ and verifies import rules.

CONFIGURABLE: Edit the RULES dict below to match your project's module structure.

Each key is a top-level directory inside backend/. The value is the set of
other top-level directories that module is allowed to import from.

Example (layered architecture):
  agent/       → may import: services/, db/
  services/    → may import: db/
  db/          → may import: nothing (leaf layer)
  auth/        → may import: db/

Exit code 0 = clean, 1 = violations found.
Error messages include the file, line number, and what to fix — so the agent
can self-repair without human intervention.
"""

import ast
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════
# CONFIGURE THIS: Define your module dependency rules
# ═══════════════════════════════════════════════════

RULES: dict[str, set[str]] = {
    "routers": {"services", "models", "config"},
    "services": {"models", "config"},
    "models": set(),
    "config": set(),
}

# Path to the source directory (relative to this script)
BACKEND = Path(__file__).resolve().parent.parent / "backend"

violations: list[str] = []


def get_module(filepath: Path) -> str | None:
    """Determine which module a file belongs to."""
    rel = filepath.relative_to(BACKEND)
    parts = rel.parts
    if len(parts) >= 2 and parts[0] in RULES:
        return parts[0]
    return None


def check_file(filepath: Path) -> None:
    """Parse a Python file and check its imports against boundary rules."""
    module = get_module(filepath)
    if module is None:
        return

    allowed = RULES[module]

    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    except SyntaxError:
        return

    for node in ast.walk(tree):
        target = None

        if isinstance(node, ast.Import):
            for alias in node.names:
                for mod in RULES:
                    if alias.name == mod or alias.name.startswith(f"{mod}."):
                        target = mod
                        break

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for mod in RULES:
                    if node.module == mod or node.module.startswith(f"{mod}."):
                        target = mod
                        break

        if target and target != module and target not in allowed:
            # Prescriptive fix: tell the agent exactly what to do
            if not allowed:
                fix = (
                    f"'{module}/' is a leaf layer — it must not import other project modules. "
                    f"Move the logic that needs '{target}/' into a higher layer (e.g., services/) "
                    f"and have that layer call both '{module}/' and '{target}/'."
                )
            else:
                fix = (
                    f"'{module}/' may only import from {sorted(allowed)}. "
                    f"Fix: create a function in one of [{', '.join(sorted(allowed))}] that wraps "
                    f"the '{target}/' call, then import that wrapper instead. "
                    f"See docs/design-docs/core-beliefs.md #3 (Data Access Is Centralized)."
                )
            violations.append(
                f"  {filepath.relative_to(BACKEND)}:{node.lineno} — "
                f"'{module}/' imports from '{target}/' which is not allowed. {fix}"
            )


def main() -> int:
    if not BACKEND.exists():
        print("backend/ directory not found — skipping import check")
        return 0

    if not RULES:
        print("No import rules configured in check_imports.py — skipping")
        print(
            "Edit the RULES dict in scripts/check_imports.py to define module boundaries."
        )
        return 0

    py_files = list(BACKEND.rglob("*.py"))
    # Exclude tests, __pycache__, and virtual environments
    py_files = [
        f
        for f in py_files
        if "test" not in str(f)
        and "__pycache__" not in str(f)
        and ".venv" not in str(f)
        and "site-packages" not in str(f)
    ]

    for f in py_files:
        check_file(f)

    if violations:
        print(f"Import boundary violations ({len(violations)}):")
        for v in violations:
            print(v)
        return 1

    print(f"Import boundaries clean ({len(py_files)} files checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
