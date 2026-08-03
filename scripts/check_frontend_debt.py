#!/usr/bin/env python3
"""Fail when tracked CSS debt grows beyond the reviewed baseline."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BUDGET_PATH = ROOT / "config/frontend_debt_budget.json"


def main() -> int:
    budgets = json.loads(BUDGET_PATH.read_text())
    findings: list[str] = []

    for relative_path, budget in sorted(budgets.items()):
        path = ROOT / relative_path
        if not path.is_file():
            findings.append(f"missing tracked stylesheet: {relative_path}")
            continue
        content = path.read_text()
        lines = len(content.splitlines())
        important = content.count("!important")
        if lines > int(budget["max_lines"]):
            findings.append(f"{relative_path}: {lines} lines > {budget['max_lines']}")
        if important > int(budget["max_important"]):
            findings.append(
                f"{relative_path}: {important} !important declarations > {budget['max_important']}"
            )

    if findings:
        print("Frontend debt budget failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1

    print(f"Frontend debt budget passed for {len(budgets)} stylesheets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
