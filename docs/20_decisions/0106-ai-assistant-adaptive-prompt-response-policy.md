# 0106 — AI Assistant adaptive prompt and response policy

Status: accepted
Date: 2026-07-13
Scope: `ai_assistant` system/developer prompts, response-style policy and obsolete provider intake guidance

## Context

After simplifying provider context in CM20, the provider still received conversational instructions that could recreate a form-like experience:

```text
fixed intake order: intent -> physical context -> activity -> plan shape
one visible question per turn
mandatory questions before optional refinement
completion pacing based on missing fields
field-specific intake rules duplicated outside tool contracts
```

Those rules made some natural responses look incorrect even when they were grounded, useful and compatible with My Scoope. They also encouraged the model to count questions and advance through stages instead of adapting to the user's actual message.

Typed draft tools already define field meaning, normalized values, persistence scope and card behavior. Current drafts and recent messages already provide conversation memory. The prompt therefore does not need to behave as a second questionnaire engine.

## Decision

Provider-facing prompts will contain broad quality, grounding and safety principles rather than a fixed conversational script.

The assistant may, according to the current turn:

```text
answer without asking a question
confirm newly understood information
ask one useful clarification
combine closely related questions when that reduces friction
request one or more typed tools
combine explanation, tool use and clarification naturally
```

There is no global provider-facing maximum of one question per turn. Questions are not automatically required because a draft field is absent. Clarification is appropriate only when ambiguity materially affects the answer or a product action.

The response-style contract keeps:

```text
clear language and readable structure
continuity with known context
transparent assumptions
natural and competent tone
no generic closing questions
no artificial urgency or missing-data countdowns
valid outer JSON response contract
```

Field meanings, enums, normalization examples and draft/card scope belong to typed tool descriptions and schemas. The developer prompt may state general tool boundaries, but it should not duplicate field-routing rules already present in those contracts.

Obsolete provider-facing builders in `conversational_intake.py` are removed. The remaining stage/question helpers are explicitly legacy deterministic fallback behavior and are not consumed by the LLM provider runtime. Their final boundary isolation remains CM23 work.

## Consequences

- The LLM can adapt its pacing to the user's message instead of following a hidden form.
- A response with zero, one or several closely related questions can be valid.
- Multi-fact messages can be handled together without forcing one-field-at-a-time dialogue.
- Tool grounding, review requirements, permissions and backend validation remain unchanged.
- Deterministic fallback behavior remains available while clearly separated from provider prompt policy.
- Replay scenarios must evolve toward behavioral invariants rather than exact question order in CM22.

## Validation contract

Tests must confirm that:

- the system prompt omits fixed intake stages and one-question instructions;
- the developer response policy describes adaptive pacing and has no numeric question cap;
- the numbered-question formatter has no hidden global cap;
- field-specific guidance remains available through typed tool contracts;
- obsolete provider intake policy builders are absent;
- current orchestrator/context/tool tests remain green.

## Related decisions

- `0096-ai-assistant-tool-oriented-intake-context.md`
- `0099-ai-assistant-llm-native-tool-intake-runtime.md`
- `0103-ai-assistant-tool-contracts-over-prompt-overstructuring.md`
- `0105-ai-assistant-provider-context-simplification.md`
