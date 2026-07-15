# 0049 — Nutrition Solver AI Assistant preview tool

Date: 2026-07-02
Status: accepted
Cycle: Nutrition Solver separation, Patch S9

## Context

S8 created a safe adapter from operational `notas.Food` rows into pure `nutrition_solver.domain.models.SolverFood` candidates. The next step is to let `ai_assistant` inspect that safe candidate set without exposing Food Catalog internals or creating proposals prematurely.

The AI Assistant already has a controlled tool registry, read-only executor and proposal executor. Solver candidate preview belongs in the read-only path because it only reads operational foods and returns bounded candidate data.

## Decision

Add a read-only AI Assistant tool:

```text
preview_nutrition_solver_candidates
```

The provider-facing tool accepts optional:

```text
search
limit
include_extended
```

Execution dispatches through:

```text
ai_assistant.application.tools.executor.ReadOnlyToolExecutor
  -> notas.application.ai_tools.read_tools.preview_nutrition_solver_candidates_tool
  -> notas.application.queries.solver_food_candidates.list_solver_food_candidates
```

The returned payload includes:

```text
solver_candidate_preview
source_boundary
```

The tool returns operational `notas.Food` IDs only. It does not return `catalog_food_id`, catalog snapshot payloads, external provider references or raw provider payloads.

## Consequences

- `ai_assistant` can preview solver-ready foods before future proposal generation.
- `nutrition_solver` remains independent and does not import `ai_assistant` or `notas`.
- The read-only executor continues to block writes and proposal creation.
- S10 can build reviewable solver proposals on top of this boundary without asking the LLM to invent final portions directly.
