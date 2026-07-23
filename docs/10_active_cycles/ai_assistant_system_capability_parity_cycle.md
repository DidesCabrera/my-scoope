# AI Assistant System Capability Parity Cycle

Status: completed
Date: 2026-07-23

## Objective

Give the AI Assistant safe, typed access to the same product capabilities available
to authenticated human users, while keeping My Scoope authoritative for resolution,
permissions, calculations, previews, persistence, entitlements and audit.

The durable interaction model is:

```text
user language
  -> LLM interpretation
  -> canonical capability catalog
  -> application query or prepare service
  -> reviewable preview
  -> trusted user approval
  -> bounded commit command
  -> verified result
```

## Non-negotiable boundaries

- AI and MCP capability declarations derive from one canonical source.
- The provider never receives internal commit-only capabilities.
- Reads validate visibility and ownership.
- Persistent nutrition changes remain proposal-first.
- Destructive, financial, sharing and administrative actions require explicit,
  risk-appropriate approval.
- Executors reuse application queries and commands; they do not call views or write
  ORM state directly.
- `food_catalog.CatalogFood` remains outside the operational AI boundary.
- Ambiguous names produce bounded choices instead of guessed identifiers.
- Every commit is idempotent, auditable and verified after execution.

## Stages

### ASP00 — Capability inventory and canonical catalog

Status: completed.

- Inventory human product actions by domain.
- Define canonical capability metadata, schemas, risk and exposure.
- Derive provider and MCP-facing declarations from the canonical catalog.
- Add contract and drift tests.

### ASP01 — Read and entity-resolution parity

Status: completed.

- Add list/search/read capabilities for Foods, Meals, DailyPlans, Programs,
  NutritionProposals, saved comparisons, calendarizations and inbox objects.
- Return bounded disambiguation choices for name-based references.
- Preserve permission and visibility boundaries.

### ASP02 — Prepare, preview, approval and commit foundation

Status: completed.

- Define versioned prepared-action contracts.
- Add one-time trusted approval metadata, expiry and idempotency.
- Keep commit capabilities hidden from the provider.
- Record sanitized audit evidence and verify post-commit state.

### ASP03 — Nutrition-core parity

Status: completed.

- Cover Food, Meal, MealFood, DailyPlan and DailyPlanMeal product actions.
- Add quantity-only DailyPlan rebalance proposals that preserve food identity.
- Reuse proposal validation/application and Nutrition Solver bounds.
- Add before/after nutrition previews.

### ASP04 — Organization and collaboration parity

Status: completed with trusted-UI handoffs for specialized composition and sharing.

- Cover Programs, weeks/days, calendarization, comparisons, proposals, sharing and
  inbox workflows.
- Apply stronger approval to sharing, deletion and proposal application.

### ASP05 — Account, billing and staff separation

Status: completed.

- Expose read-only account, plan, credit and subscription state.
- Prepare checkout navigation and subscription cancellation behind trusted approval.
- Keep staff analytics/operations in a separate staff-only capability namespace.

### ASP06 — Parity verification and rollout

Status: completed. Runtime activation remains governed by the existing rollout flags.

- Maintain an executable matrix from human action to application service and AI
  capability.
- Add domain, integration, permission, idempotency and replay coverage.
- Run focused suites, Django checks, regressions and the full CI boundary.
- Promote accepted contracts into current docs and record durable decisions.

## Acceptance criteria

- Every in-scope human action is classified as supported, intentionally UI-only,
  staff-only or externally gated.
- Supported actions have typed schemas, ownership checks, risk classification and
  automated tests.
- No provider-exposed capability can directly apply a final domain mutation.
- Chat and MCP declarations cannot drift from the canonical catalog.
- The request “increase my DailyPlan by 200 kcal, preserving foods and changing only
  quantities” produces a reviewable, validated proposal and never changes the plan
  before explicit approval.

## Delivered result

- `ai_assistant.domain.capabilities` classifies all current human product areas as
  autonomous read, reviewable proposal, prepared action, trusted-UI handoff or
  staff-only.
- `ai_assistant.application.tools.registry` is the sole executable declaration source;
  `mcp_server.myscoope_mcp.tools` is an adapter.
- Chat renders proposal and prepared-action cards from controlled tool results.
- `AIPreparedAction` provides expiry, ownership, stale-target protection, replay
  protection and post-commit result evidence.
- Proportional calorie proposals operate only on DailyPlan Meal snapshots.
- Account/billing is read-only to the assistant; checkout/cancellation and all staff
  operations remain on their dedicated trusted surfaces.

## Activation

The implementation preserves the existing safe rollout gates. To exercise these
capabilities in an LLM environment, that environment must explicitly enable its LLM
chat mode and reviewable tools. The deterministic default remains the rollback path:

```text
AI_ASSISTANT_CHAT_ENGINE_MODE=llm_preview
AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS=true
```

Production continues to require the separate production rollout configuration.
