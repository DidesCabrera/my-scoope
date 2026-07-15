# 0039 · AI Assistant AI credits by membership

Status: accepted  
Date: 2026-07-02

## Context

Patch 56 started recording AI usage by turn, model, provider, `action_type`, tokens and optional estimated USD cost. Patch 57 added technical guardrails. Patch 58 connected `llm_preview` to the existing chat with measurement and guardrails active.

The next step is to express commercial AI usage as **AI credits**, not tokens. Tokens remain an internal cost metric because they are provider-specific and too technical for users.

## Decision

Patch 59 introduces a first membership-aware AI credit layer inside `ai_assistant`.

The commercial unit is:

```text
AI credits
```

The internal observability units remain:

```text
input_tokens
cached_input_tokens
output_tokens
total_tokens
estimated_cost_usd
provider/model
action_type
```

Credits are implemented behind settings and remain disabled by default:

```text
AI_ASSISTANT_CREDITS_ENABLED = False
```

This keeps staging safe while My Scoope continues learning real usage costs.

## Implementation

Patch 59 adds:

```text
ai_assistant.application.credits.DjangoAICreditService
ai_assistant.models.AIUserCreditQuota
ai_assistant.models.AICreditLedger
AIUsageEvent.charged_credits
AIUsageEvent.credit_plan_code
```

`DjangoAICreditService` does two things:

1. Preflight check before a provider call when credits are enabled.
2. Post-turn charge after `AIUsageEvent` is persisted for a completed turn.

If a user exceeds the configured monthly or daily quota, the orchestrator blocks the turn before calling the external provider and records a `blocked` usage event.

## Plan resolution

The initial resolver maps users to credit plans using, in order:

```text
profile.plan.name
profile.plan.role
profile.role
default
```

Plan names are normalized to stable lowercase codes. Settings can later map custom plan names through aliases.

## Settings

Patch 59 adds:

```text
AI_ASSISTANT_CREDITS_ENABLED
AI_ASSISTANT_USD_PER_AI_CREDIT
AI_ASSISTANT_DEFAULT_CREDITS_PER_TURN
AI_ASSISTANT_CREDIT_PLANS
AI_ASSISTANT_CREDIT_PLAN_ALIASES
AI_ASSISTANT_ACTION_CREDIT_MULTIPLIERS
```

Default credit plans exist for `default`, `member` and `nutritionist`, but enforcement is disabled until `AI_ASSISTANT_CREDITS_ENABLED=True`.

## Consequences

- My Scoope now has the primitives needed to control AI usage by membership.
- Users are not exposed to tokens.
- Completed turns can be charged as credits.
- Blocked quota turns do not call the provider.
- Provider errors and technical blocks are not charged as completed AI usage.
- Patch 60 can focus on admin/dashboard consumption views rather than inventing the quota model.
