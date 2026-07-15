# 0116 — Proposal complexity must survive tool-result state synchronization

## Status

Accepted during the CM24 real-provider validation gate.

## Context

The seventh live CM24 run proved that the provider-native tool path was healthy:

- `update_proposal_preferences` executed successfully;
- the proposal-preferences card showed `complexity_level=low` for “algo simple”;
- provider transport, tool grounding, cards, limits and usage observability all passed.

Despite that evidence, the final `NutritionBrief` still exposed `complexity_level=None` and therefore remained not ready for proposal creation.

Code inspection found that the value was not lost in OpenAI, the native function schema or the proposal draft tool. The local synchronization function `_apply_proposal_preferences_to_brief()` copied goal, entity, meals, energy and nutrition targets, but its explicit allowlist omitted `complexity_level`. The companion `nutrition_brief_patch` could not repair the omission because fields already present in `proposal_preferences` are intentionally removed from that redundant patch to preserve their provenance.

## Decision

`complexity_level` is added to the canonical proposal-preference fields synchronized into `NutritionBrief`, including its original `field_sources` provenance.

The regression test must cover the complete boundary:

```text
provider-native proposal tool result
-> proposal_preferences.complexity_level=low
-> NutritionBrief.complexity_level=low
-> field_sources.complexity_level preserved
-> proposal readiness may become true
```

## Consequences

- No provider prompt or function schema change is required.
- No local semantic parser, regex or recovery from assistant prose is introduced.
- Card presentation and state mutation remain separate responsibilities.
- The fix closes a server-side state-projection omission rather than changing LLM behavior.
- CM24 still requires one final live run and explicit human transcript disposition before closure.
