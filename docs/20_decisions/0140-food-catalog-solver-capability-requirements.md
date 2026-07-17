# 0140 - Food Catalog-Solver capability requirements

Status: accepted
Date: 2026-07-16
Cycle: NSO01

## Decision

Nutrition Solver declares required and optional food features through a pure, versioned
requirements contract. Food Catalog owns curated facts and confidence; `notas` owns the explicit
operational snapshot and adapter; the solver owns eligibility and missing-feature behavior.

Required features may exclude a candidate or make a problem impossible. Optional features use a
neutral default or warning. Missing values are never invented by the runtime LLM.

The relationship is intentionally close but not a direct model dependency:

```text
Food Catalog capabilities -> notas.Food snapshot -> Solver feature assessment
```
