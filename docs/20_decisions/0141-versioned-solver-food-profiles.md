# 0141 - Versioned Solver food profiles

Status: accepted
Date: 2026-07-16
Cycle: NSO02

## Decision

Represent solver-facing food enrichment as a pure `SolverFoodProfile`. Each feature carries its
value, confidence, source, version and whether it was derived. A food may expose multiple
functional roles and meal affinities; no single category is treated as complete truth.

Absent features remain absent. Runtime defaults are allowed only when the requirements contract
declares neutral behavior, and derived values identify the deterministic rule version that
produced them.
