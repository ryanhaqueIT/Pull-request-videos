#!/usr/bin/env python3
"""check_golden_principles.py — Enforce golden principles mechanically.

Scans Python files in backend/ for violations of golden principles.
Error messages are actionable — the agent can read them and know exactly what to fix.

Checks:
1. No print() in non-test files (use logger.info instead)
2. No hardcoded secrets patterns (API_KEY=, SECRET=, PASSWORD= in strings)
3. Type hints on all function definitions
4. No bare except clauses (must specify exception type)

Exit code 0 = clean, 1 = violations found.
"""

import ast
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"

violations: list[str] = []


def check_no_print(filepath: Path, tree: ast.AST) -> None:
    """Principle: No print() in production code."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "print":
                violations.append(
                    f"  {filepath.relative_to(BACKEND)}:{node.lineno} — "
                    f"print() found. Fix: replace with logger.info() or logger.error(). "
                    f"Add these two lines at the top of the file if not present:\n"
                    f"    import logging\n"
                    f"    logger = logging.getLogger(__name__)\n"
                    f"  Then replace print(...) with logger.info(...). "
                    f"See docs/RELIABILITY.md (Logging section)."
                )


def check_no_hardcoded_secrets(filepath: Path) -> None:
    """Principle: No secrets in code."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    patterns = [
        (r'["\'](?:sk-|ak_|mk_)[a-zA-Z0-9]{20,}["\']', "API key literal"),
        (
            r'(?:API_KEY|SECRET_KEY|PASSWORD|AUTH_TOKEN)\s*=\s*["\'][^"\']{8,}["\']',
            "Hardcoded secret assignment",
        ),
        (
            r'(?:client_secret|private_key)\s*=\s*["\'][^"\']{8,}["\']',
            "Hardcoded credential",
        ),
    ]
    for pattern, desc in patterns:
        for match in re.finditer(pattern, content):
            line_num = content[: match.start()].count("\n") + 1
            violations.append(
                f"  {filepath.relative_to(BACKEND)}:{line_num} — "
                f"{desc} detected. Use environment variables or a secret manager. "
                f"Example: os.environ['SECRET_KEY'] or settings.SECRET_KEY"
            )


def check_type_hints(filepath: Path, tree: ast.AST) -> None:
    """Principle: Type hints on all function definitions."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip dunder methods (except __init__) and private methods
            if node.name.startswith("_") and node.name != "__init__":
                continue
            if node.returns is None and node.name != "__init__":
                violations.append(
                    f"  {filepath.relative_to(BACKEND)}:{node.lineno} — "
                    f"Function '{node.name}' missing return type hint. "
                    f"Fix: add '-> ReturnType' to the function signature. "
                    f"Common return types: -> None, -> str, -> dict, -> list[str], -> bool. "
                    f"For async functions returning nothing, use -> None."
                )


def check_no_bare_except(filepath: Path, tree: ast.AST) -> None:
    """Principle: No bare except — must specify exception type."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            violations.append(
                f"  {filepath.relative_to(BACKEND)}:{node.lineno} — "
                f"Bare 'except:' clause. Fix: specify the exception type. "
                f"Use 'except ValueError as e:' for validation errors, "
                f"'except OSError as e:' for I/O errors, "
                f"or 'except Exception as e:' as a last resort (never bare 'except:'). "
                f"Always log the error: logger.error('Failed: %s', e). "
                f"See docs/RELIABILITY.md (Error Handling section)."
            )


def main() -> int:
    if not BACKEND.exists():
        print("backend/ directory not found — skipping golden principles check")
        return 0

    py_files = list(BACKEND.rglob("*.py"))
    py_files = [
        f
        for f in py_files
        if "__pycache__" not in str(f)
        and ".venv" not in str(f)
        and "site-packages" not in str(f)
        and "test" not in f.name  # Don't enforce on test files
        and f.name != "__init__.py"
    ]

    for filepath in py_files:
        try:
            tree = ast.parse(
                filepath.read_text(encoding="utf-8"), filename=str(filepath)
            )
        except SyntaxError:
            continue

        check_no_print(filepath, tree)
        check_no_hardcoded_secrets(filepath)
        check_type_hints(filepath, tree)
        check_no_bare_except(filepath, tree)

    if violations:
        print(f"Golden principle violations ({len(violations)}):")
        for v in violations:
            print(v)
        return 1

    print(f"Golden principles clean ({len(py_files)} files checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
