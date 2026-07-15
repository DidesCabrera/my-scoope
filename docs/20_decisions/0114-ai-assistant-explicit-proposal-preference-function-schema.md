# 0114 — Explicit proposal-preference function schema

Status: accepted  
Date: 2026-07-13  
Scope: provider-native `update_proposal_preferences`, CM24 live validation

## Context

The fifth CM24 live run passed provider health, native function-call transport, grouped tool execution, direction changes, card pacing and post-tool error recovery. Only the grouped-data scenario remained open:

```text
User says “4 comidas y algo simple”
-> update_proposal_preferences executes
-> goal, entity and meals are synchronized
-> complexity_level remains empty
```

The runtime tool already accepted and normalized `complexity_level=low|medium|high`. The remaining gap was provider-facing: the native function declaration described `updates` as a generic object and listed its fields only in prose. The model recognized “simple” in visible copy but did not include the corresponding key in the function arguments.

## Decision

`update_proposal_preferences.updates` exposes its proposal fields as explicit JSON Schema properties. In particular:

```text
complexity_level: low | medium | high
algo simple / sencillo -> low
intermedio / intermedia -> medium
elaborado / complejo -> high
```

The same schema explicitly exposes goal, requested entity, meals, energy adjustment, optional targets and notes. Unknown update keys are rejected at the provider contract boundary, while My Scoope remains the canonical normalizer and validator after the call arrives.

The developer-facing operational example also demonstrates that grouped input such as “4 comidas y algo simple” belongs in one `update_proposal_preferences` call containing both `meals_per_day=4` and `complexity_level=low`.

## Payload constraint

The provider tool catalog is part of the protected input budget. The explicit schema is intentionally compact. It must remain below the existing technical limits and must not increase the ordinary product token cap.

This decision does not:

- parse the user's sentence locally;
- infer complexity after the provider response;
- add a deterministic intake rule;
- create a separate tool for every proposal field;
- change persistent profile or preference memory.

## Consequences

- Proposal complexity is carried through the same native function channel already validated by CM24.
- Visible prose can no longer be the only place where the provider represents “simple”.
- The tool contract becomes more reusable for other AI/MCP clients because supported fields are machine-readable rather than prose-only.
- A sixth complete live run is required before CM24 can pass the automated gate, followed by human transcript review.
