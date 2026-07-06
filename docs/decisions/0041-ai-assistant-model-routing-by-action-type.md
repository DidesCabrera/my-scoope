# 0041 · AI Assistant model routing by action_type

Status: accepted  
Date: 2026-07-02

## Context

Patch 56 introduced `AIUsageEvent`, Patch 59 introduced AI credits, and Patch 60 added an internal usage dashboard. With that foundation in place, My Scoope can start optimizing cost without exposing tokens to the user.

The key requirement is to route different AI functions to different provider/model choices. Simple chat or preview turns may use a cheaper model, while higher-risk proposal or tool-heavy turns may remain on a stronger model. This must be configurable and reversible, because real cost/performance data will come from production-like usage.

## Decision

Patch 61 introduces an optional model routing layer based on `action_type`.

The router resolves a route before the provider call:

```text
AssistantTurnRequest.metadata.action_type
  -> AI model route
  -> provider/model/max_output_tokens
  -> provider gateway
  -> AIUsageEvent records actual provider/model/cost
```

The setting is:

```python
AI_ASSISTANT_LLM_MODEL_ROUTES = {
    "default": {
        "provider": AI_ASSISTANT_LLM_PROVIDER,
        "model": AI_ASSISTANT_OPENAI_MODEL,
        "max_output_tokens": AI_ASSISTANT_MAX_OUTPUT_TOKENS,
        "reason": "default_external_llm_route",
    },
    "assistant.chat": {
        "provider": "openai",
        "model": "<cheap-model>",
        "max_output_tokens": 500,
        "reason": "low_cost_chat",
    },
}
```

The default route preserves current behavior. Action-specific routes can be added later in deployment settings after observing cost and quality.

Prefix routes are also supported:

```python
"assistant.explain.*": {"provider": "openai", "model": "<cheap-model>"}
```

A route may lower `max_output_tokens`, but it cannot exceed the global technical guardrail from the orchestrator config.

## Consequences

- Cost optimization becomes a configuration concern instead of hard-coded branching.
- `AIUsageEvent` remains the source of truth for actual provider/model/cost after the call.
- Credits remain commercial units; tokens and model pricing stay internal.
- The preview can be moved to cheaper models without changing chat templates.
- Stronger models can be reserved for proposal creation, tool-heavy flows, or higher-risk actions.
- The feature is safe by default because only the default route is configured in base settings.

## Non-goals

- This patch does not choose final commercial prices.
- This patch does not expose model names or tokens to end users.
- This patch does not activate a production rollout globally.
- This patch does not make provider pricing assumptions.
