#!/usr/bin/env python3
"""Reject accidental growth in reviewed backend/mobile hotspots."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BUDGET_PATH = ROOT / "config/backend_debt_budget.json"


def main() -> int:
    budgets = json.loads(BUDGET_PATH.read_text())
    findings = []
    for relative_path, budget in sorted(budgets.items()):
        path = ROOT / relative_path
        if not path.is_file():
            findings.append(f"missing tracked hotspot: {relative_path}")
            continue
        lines = len(path.read_text().splitlines())
        if lines > int(budget["max_lines"]):
            findings.append(f"{relative_path}: {lines} lines > {budget['max_lines']}")

    if findings:
        print("Backend debt budget failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1

    print(f"Backend debt budget passed for {len(budgets)} hotspots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
