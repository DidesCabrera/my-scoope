#!/usr/bin/env python3
"""Keep browser scenarios configurable and condition-driven."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
E2E_ROOT = ROOT / "e2e"
FORBIDDEN_TEXT = (
    "wait_for_timeout(",
    "e2e/auth/state.json",
    "storage_state_path",
)
FIXED_APP_ID = re.compile(r"/app/(?:meals|dailyplans)/\d+")


def main() -> int:
    findings: list[str] = []
    for path in sorted(E2E_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        content = path.read_text()
        relative = path.relative_to(ROOT)
        for forbidden in FORBIDDEN_TEXT:
            if forbidden in content:
                findings.append(f"{relative}: contains {forbidden!r}")
        if FIXED_APP_ID.search(content):
            findings.append(f"{relative}: contains a fixed database object ID in an app URL")

    if findings:
        print("Browser contract check failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("Browser contract check passed: configurable IDs, no fixed sleeps or persisted auth files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
