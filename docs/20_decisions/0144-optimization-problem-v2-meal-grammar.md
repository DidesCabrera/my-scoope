# 0144 - Optimization Problem V2 and meal grammar

Status: accepted
Date: 2026-07-16
Cycle: NSO05

## Decision

Model optimization as nutrient ranges, explicit meal slots, hard constraints and hierarchical
objective tiers. Meal structure is validated through archetypes whose required components accept
groups of capabilities, allowing one food to satisfy multiple functional signals without forcing
one exclusive category.

The contract is pure and backend-independent. Heuristic and CP-SAT implementations consume the
same problem boundary.
