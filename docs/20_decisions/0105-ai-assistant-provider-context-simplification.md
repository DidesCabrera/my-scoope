# 0105 — AI Assistant provider context simplification

Status: accepted
Date: 2026-07-13
Scope: `ai_assistant` provider context, nutrition intake objects and LLM orchestration

## Context

The LLM-native runtime already removed deterministic follow-up questions, but the provider context still rebuilt much of the old questionnaire logic through duplicated structures:

```text
known_fields
do_not_ask_again_fields
profile_completion policy
missing-profile counts
recommended tool sequences
long rule arrays
instructional meanings attached to cards
readiness and pending-question flags
```

Most of this information was already present in the actual draft objects, visible cards and typed tool contracts. Repeating it as policy encouraged the provider to follow a fixed completion sequence instead of adapting naturally to the user's request.

The context also had a technical inconsistency: nested draft and card objects could be truncated by the generic sanitization depth before reaching the provider. This meant the runtime could send policy about objects while omitting parts of the objects themselves.

## Decision

This decision supersedes the provider payload shape introduced by `0096` where it exposed recommended tool sequences and duplicated completion guidance. The underlying tool-oriented architecture remains accepted.

Provider-facing nutrition intake context will expose state and capabilities, not a reconstructed interviewer.

The `tool_oriented_intake` context contains:

```text
assistant role
current profile/preference/proposal drafts
small work context such as proposal subject
concise semantics for present and absent values
```

It no longer contains:

```text
do_not_ask_again_fields
profile_completion
recommended_tool_sequence
rules arrays
computed readiness/pending-question policy
card instructional_meaning
```

Values present in `current_drafts` are facts already known for the current conversation. Values absent from a draft are not automatically mandatory; the LLM decides whether asking for one is useful to the user's current work. New facts must still be recorded through typed tools.

For `ai_nutrition_intake`, the raw `nutrition_brief` is not duplicated beside the draft objects in provider context. It remains the internal conversation source of truth and continues to receive tool-result synchronization. Other surfaces may receive a compact sanitized brief when needed.

Runtime capabilities are expressed once through a small set of positive flags:

```text
tools enabled
draft state is conversation-scoped
cards require explicit presentation tools
proposal creation availability
persistent writes require approval
```

The provider sanitizer keeps bounding, sensitive-key filtering, list limits and text limits, but admits enough nested depth for current drafts, field provenance, recent messages and visible chat objects to survive intact.

## Consequences

- The LLM receives real objects instead of duplicated slot-completion policy.
- Missing data is no longer framed as an automatic questionnaire backlog.
- Typed tool descriptions remain the source for field meaning and normalized values.
- Existing backend validation, permissions, technical limits and proposal-readiness checks remain unchanged.
- Recent cards preserve their state for contextual references without embedding instructions about what the model must ask next.
- Provider context becomes smaller, more legible and better aligned with MCP/future AI tool reuse.
- Prompt and response-style cleanup remains a separate CM21 responsibility.

## Validation contract

Tests must confirm that:

- current draft values reach the provider-safe payload without truncation;
- sensitive nested keys remain filtered;
- intake context omits duplicated brief/completion structures;
- recent cards expose visible state but no conversational instruction;
- proposal capability and approval boundaries remain present.

## Related decisions

- `0096-ai-assistant-tool-oriented-intake-context.md`
- `0099-ai-assistant-llm-native-tool-intake-runtime.md`
- `0103-ai-assistant-tool-contracts-over-prompt-overstructuring.md`
- `0104-ai-assistant-draft-update-card-sharing-boundary.md`
