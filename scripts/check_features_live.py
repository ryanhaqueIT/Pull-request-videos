#!/usr/bin/env python3
"""Live feature verification — tests features against a running app instance.

Reads .harness/feature_list.json and executes each feature's steps against
the running backend. This is the strongest verification gate: it proves
features actually work end-to-end, not just that tests pass.

Usage:
    python scripts/check_features_live.py --summary
    python scripts/check_features_live.py --url http://localhost:8000
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURE_LIST = REPO_ROOT / ".harness" / "feature_list.json"


def get_backend_url() -> str:
    """Get the backend URL from instance-metadata or default."""
    meta_file = REPO_ROOT / "instance-metadata.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text())
        return meta.get("backend_url", "http://localhost:8000")
    return "http://localhost:8000"


def check_health(url: str) -> tuple[bool, str]:
    """F001: GET /health returns healthy status."""
    try:
        import httpx

        resp = httpx.get(f"{url}/health", timeout=10)
        if resp.status_code != 200:
            return False, f"Expected 200, got {resp.status_code}"
        body = resp.json()
        if body.get("status") != "healthy":
            return False, f"Expected status=healthy, got {body}"
        return True, f"HTTP 200, {body}"
    except Exception as e:
        return False, str(e)


def check_structured_error(url: str) -> tuple[bool, str]:
    """F002: API returns structured error with correlation_id."""
    try:
        import httpx

        resp = httpx.get(f"{url}/nonexistent-path-for-testing", timeout=10)
        if resp.status_code != 404:
            return False, f"Expected 404, got {resp.status_code}"
        body = resp.json()
        if "correlation_id" not in body:
            return False, f"Missing correlation_id in {body}"
        return True, f"HTTP 404 with correlation_id={body['correlation_id'][:8]}..."
    except Exception as e:
        return False, str(e)


def check_correlation_header(url: str) -> tuple[bool, str]:
    """F002 bonus: X-Correlation-ID header present."""
    try:
        import httpx

        resp = httpx.get(f"{url}/health", timeout=10)
        cid = resp.headers.get("x-correlation-id", "")
        if not cid:
            return False, "Missing X-Correlation-ID header"
        return True, f"X-Correlation-ID: {cid[:8]}..."
    except Exception as e:
        return False, str(e)


def check_agent_endpoint(url: str) -> tuple[bool, str]:
    """Bonus: POST /api/agents/run accepts requests."""
    try:
        import httpx

        resp = httpx.post(
            f"{url}/api/agents/run",
            json={"url": "http://localhost:3000", "mode": "direct"},
            timeout=10,
        )
        if resp.status_code != 200:
            return False, f"Expected 200, got {resp.status_code}"
        body = resp.json()
        if body.get("status") != "accepted":
            return False, f"Expected status=accepted, got {body}"
        return True, f"HTTP 200, session_id={body.get('session_id')}"
    except Exception as e:
        return False, str(e)


def check_control_plane_sessions(url: str) -> tuple[bool, str]:
    """Bonus: POST /api/control/sessions creates a session."""
    try:
        import httpx

        resp = httpx.post(
            f"{url}/api/control/sessions",
            json={"repo_url": "https://github.com/test/repo"},
            timeout=10,
        )
        if resp.status_code != 200:
            return False, f"Expected 200, got {resp.status_code}"
        body = resp.json()
        if "session_id" not in body or "session_token" not in body:
            return False, f"Missing session_id/session_token in {body}"
        return True, f"session_id={body['session_id']}, token present"
    except Exception as e:
        return False, str(e)


# Map feature IDs to live check functions
LIVE_CHECKS = {
    "F001": check_health,
    "F002": check_structured_error,
}

# Extra checks beyond the feature list
EXTRA_CHECKS = [
    ("Correlation ID header", check_correlation_header),
    ("Agent endpoint", check_agent_endpoint),
    ("Control plane sessions", check_control_plane_sessions),
]


def main() -> int:
    """Run live feature checks."""
    url = "http://localhost:8000"
    summary_mode = False

    for arg in sys.argv[1:]:
        if arg == "--summary":
            summary_mode = True
        elif arg.startswith("--url="):
            url = arg.split("=", 1)[1]
        elif arg.startswith("--url"):
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                url = sys.argv[idx + 1]

    if not FEATURE_LIST.exists():
        print("ERROR: .harness/feature_list.json not found")
        return 1

    features = json.loads(FEATURE_LIST.read_text())
    total = 0
    passed = 0
    failed = 0

    print("=" * 50)
    print(" Live Feature Verification")
    print(f" Target: {url}")
    print("=" * 50)

    # Check features from feature_list.json
    for feat in features.get("features", []):
        fid = feat["id"]
        desc = feat["description"]

        if fid in LIVE_CHECKS:
            total += 1
            ok, detail = LIVE_CHECKS[fid](url)
            if ok:
                passed += 1
                print(f"  PASS  {fid}: {desc}")
                if not summary_mode:
                    print(f"        {detail}")
            else:
                failed += 1
                print(f"  FAIL  {fid}: {desc}")
                print(f"        {detail}")
        else:
            # Features without live checks are skipped (they're verified by unit tests)
            if not summary_mode:
                print(f"  SKIP  {fid}: {desc} (no live check — verified by unit tests)")

    # Run extra checks
    print()
    print("  Extra endpoint checks:")
    for name, check_fn in EXTRA_CHECKS:
        total += 1
        ok, detail = check_fn(url)
        if ok:
            passed += 1
            print(f"  PASS  {name}")
            if not summary_mode:
                print(f"        {detail}")
        else:
            failed += 1
            print(f"  FAIL  {name}")
            print(f"        {detail}")

    print()
    print(f"Live features: {passed}/{total} passing")

    if failed > 0:
        print(f"FAILED: {failed} live check(s) did not pass")
        return 1

    print("All live checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
