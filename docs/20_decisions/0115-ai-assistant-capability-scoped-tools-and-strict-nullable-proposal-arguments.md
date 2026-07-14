# 0115 — Capability-scoped tools and strict nullable proposal arguments

Status: accepted

## Context

The sixth CM24 live run confirmed that provider-native function calling, tool execution, cards, state transitions and post-tool recovery were stable. Two related gaps remained in the grouped-data scenario:

1. `update_proposal_preferences` executed, but the provider omitted `complexity_level` even though the user said “algo simple” and the visible response recognized it.
2. The next turn was blocked before reaching the provider because My Scoope attached the complete provider tool catalog, including reviewable proposal tools that CM24 had explicitly disabled.

The first issue shows that an explicit but non-strict optional property can still disappear from best-effort function arguments. The second shows that the provider-facing catalog must mirror the capabilities the orchestrator can actually execute; disabled tools are not harmless documentation because their schemas consume context and may be selected by the model.

## Decision

### Provider catalog mirrors runtime capability flags

When `enable_reviewable_proposal_tools` is false, tools in the `proposal` category are not sent to the provider and are not listed in the developer prompt. Draft and read capabilities remain available.

This is capability filtering, not conversational routing. My Scoope does not infer the next question or narrow tools based on a scripted intake stage; it simply avoids advertising operations that the current runtime would reject.

### Proposal updates use a strict nullable provider schema

`update_proposal_preferences` keeps its provider-independent local input contract, but its OpenAI-facing declaration uses a compact strict schema:

- `strict=true`;
- every object has `additionalProperties=false`;
- all proposal update properties are required by the schema;
- fields not stated by the user are represented as `null`;
- My Scoope removes null values before local validation and merge;
- `complexity_level` remains `low|medium|high|null`, with “algo simple/sencillo” documented as `low`.

This forces the provider to make each proposal field explicit without forcing My Scoope to invent a value. It also preserves partial updates: nullable fields do not overwrite existing draft state.

## Consequences

- No local regex/parser is added to recover “simple” from assistant prose.
- No global input-token limit is increased.
- Disabled proposal schemas no longer consume provider context.
- The strict function call can carry `complexity_level=low` while unrelated fields remain null and are discarded safely.
- The complete provider catalog remains available when reviewable proposal tools are enabled.
- CM24 requires a seventh live run and human transcript review before closure.
