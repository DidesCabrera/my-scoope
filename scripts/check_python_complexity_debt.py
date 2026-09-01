#!/usr/bin/env python3
"""Reject new or worsened Python functions above the reviewed complexity threshold."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BUDGET_PATH = ROOT / "config/python_complexity_budget.json"
SCAN_PATHS = (
    "accounts",
    "admin_analytics",
    "admin_operations",
    "ai_assistant",
    "billing",
    "core",
    "email_delivery",
    "food_catalog",
    "miapp",
    "mobile_api",
    "notas",
    "nutrition_solver",
    "mcp_server/myscoope_mcp",
)
MESSAGE_PATTERN = re.compile(r"`(?P<name>[^`]+)` is too complex \((?P<score>\d+) > 15\)")


def main() -> int:
    budgets: dict[str, int] = json.loads(BUDGET_PATH.read_text())
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            *SCAN_PATHS,
            "--select",
            "C901",
            "--config",
            "lint.mccabe.max-complexity=15",
            "--output-format",
            "json",
            "--no-cache",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode not in {0, 1}:
        print(process.stderr or process.stdout, file=sys.stderr)
        return process.returncode

    findings: list[str] = []
    observed: set[str] = set()
    for diagnostic in json.loads(process.stdout):
        match = MESSAGE_PATTERN.fullmatch(diagnostic["message"])
        if match is None:
            findings.append(f"unrecognized Ruff diagnostic: {diagnostic['message']}")
            continue
        relative_path = Path(diagnostic["filename"]).relative_to(ROOT).as_posix()
        key = f"{relative_path}::{match.group('name')}"
        score = int(match.group("score"))
        observed.add(key)
        allowed = budgets.get(key)
        if allowed is None:
            findings.append(f"new complex function: {key} ({score})")
        elif score > allowed:
            findings.append(f"{key}: complexity {score} > budget {allowed}")

    stale = sorted(set(budgets) - observed)
    if stale:
        findings.extend(f"remove improved/stale complexity allowance: {key}" for key in stale)

    if findings:
        print("Python complexity budget failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1

    print(f"Python complexity budget passed with {len(observed)} reviewed exceptions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
