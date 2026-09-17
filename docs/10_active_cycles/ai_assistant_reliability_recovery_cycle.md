# AI Assistant Reliability Recovery Cycle

Status: active · ARR00-ARR05 completed locally; ARR06 real-provider/staging gate pending
Date: 2026-09-16
Owner: Product / AI Assistant / Nutrition experience
Branch: `fix/ai-assistant-context-tool-alignment`

## Objective

Recover the assistant as an outcome-oriented product capability by aligning client
memory, provider-visible tools, trusted persistence, presentation and operational
evidence. Safety boundaries remain explicit, but a guardrail must never make a valid
capability invisible or leave the reason for a blocked outcome unknowable.

```text
user objective
  -> canonical client-memory workspace
  -> relevant visible tools
  -> bounded execution and reasoned guardrails
  -> visible draft/proposal/action
  -> trusted approval for persistence
  -> outcome trace and end-to-end validation
```

## Baseline findings

1. Provider context and preference tools used different field vocabularies.
2. The nutrition-intake tool filter hid profile reads and card tools even though the
   canonical registry and documentation declared them available.
3. Preference memory was conversation-only; `commit_preference_update` was described
   as planned but did not exist.
4. Profile facts and preference facts had asymmetric persistence contracts.
5. Unit tests proved local contracts but did not prove completion of real user
   objectives against the live provider.
6. Tool telemetry described calls and errors, but not whether the active product
   objective advanced.

## Non-negotiable boundaries

- Persistent writes require a trusted UI approval event.
- Provider-exposed tools cannot invoke commit capabilities.
- Approved preferences are not automatically sent to an external provider on every
  turn. The read capability is available when the user asks to use saved preferences.
- Allergies and restrictions remain typed values; proposal and solver layers must
  treat their safety meaning explicitly.
- `notas.Food` remains the operational food universe; no Food Catalog boundary changes.
- A cycle stage is not complete merely because fake-provider tests pass.

## Stages

### ARR00 — Register cycle and reproducible baseline

Status: completed locally.

- Record the audit findings, branch and acceptance criteria.
- Preserve the clean `staging` baseline and use focused validation while iterating.
- Define the real-provider/staging gate separately from repository completion.

### ARR01 — Canonical client-memory contract

Status: completed locally.

- Add `ai_assistant_client_memory.v2` as the provider/tool field authority.
- Make context builder, profile tools and preference tools consume that contract.
- Project legacy `NutritionBrief` fields into canonical preference names.
- Preserve typed dietary pattern, allergy and meal-organization values through
  conversation serialization instead of reducing them only to prose notes.
- Upgrade the provider workspace to `ai_assistant_workspace.v2`.

Acceptance evidence:

- context and tool schemas use identical preference keys;
- provenance survives conversation round-trips;
- regression tests reject the old mixed vocabulary.

### ARR02 — Restore capability visibility

Status: completed locally.

- Expose profile read, approved-preference read and deliberate card tools in the
  nutrition-intake core tool set.
- Keep commit tools hidden from the provider.
- Add contract tests for the exact intake tool catalog.

Acceptance evidence:

- a request to use the user's ficha can see `read_user_profile_context`;
- a request to use saved preferences can see `read_user_preference_context`;
- profile/preference/proposal cards remain optional presentation capabilities;
- direct commit remains impossible through provider function calling.

### ARR03 — Durable preference memory with trusted approval

Status: completed locally.

- Add one per-user `NutritionPreferenceProfile` using canonical, normalized fields.
- Add read and internal commit tools.
- Require `preference_card_button` trusted approval metadata for commit.
- Add web and mobile approval paths and return a committed card whose provenance is
  `profile`.
- Do not preload or export approved preference memory without contextual user intent.

Acceptance evidence:

- an approved draft is readable in a later chat;
- an unapproved draft never persists;
- provider tool declarations exclude the commit tool;
- mobile and web cards expose a trusted save action.

### ARR04 — Outcome and guardrail trace

Status: completed locally.

- Attach `ai_assistant_outcome_trace.v1` to healthy orchestrated turns.
- Record objective, state, blocking-field count, bounded tool outcomes and proposal
  creation without storing prompt text or raw arguments.
- Persist only a safe scalar projection in `AIUsageEvent.metadata`.

Outcome states:

```text
outcome_created
workspace_advanced
awaiting_blocking_information
guardrail_blocked
response_only
```

### ARR05 — Client parity and objective replays

Status: completed locally.

- Keep preference-card approval available on web and mobile.
- Validate canonical memory, profile reads, preference persistence, proposal creation,
  ambiguous restraint and post-tool response behavior.
- Treat replay success as an invariant chain, not a required phrase match.

Required replay scenarios:

1. Use my ficha and create a reviewable fat-loss plan.
2. Remember vegan pattern plus peanut allergy, approve it, then use it in a later chat.
3. Increase an existing plan by 200 kcal while preserving foods.
4. Ask an ambiguous question and execute no read/write/card.
5. Provide the last blocking physical fact and create the proposal in the same turn.

### ARR06 — Real-provider staging gate and closure

Status: pending external environment.

- Run the five ARR05 scenarios with the configured production candidate model.
- Require no systematic post-tool fallback and no unknown/repeated known facts.
- Inspect outcome traces, abandonment, repeated questions, corrections and proposal
  application.
- Close only after a human review of complete transcripts and cards.

The local environment currently selects OpenAI without an API key. ARR06 therefore
cannot be truthfully marked complete from repository-only evidence.

## Executed evidence — 2026-09-16

- Focused AI, context, registry, executor, persistence, API and outcome suites:
  74 tests passed during implementation.
- Integrated assistant/mobile API and architecture suites: 293 tests passed.
- Mobile visual contract: 3 tests passed.
- Mobile iteration gate: lint, TypeScript and 121 tests passed.
- Django repository gate: hygiene, scope, debt budgets, browser contract, system
  checks, migration drift, OpenAPI freshness and document registry passed; the
  97-test regression gate and 1,959-test full suite passed.
- Account deletion explicitly erases `NutritionPreferenceProfile`; its coverage and
  behavior tests passed as part of the final repository gate.
- `git diff --check` passed.

These results close the repository and client-parity stages. They do not replace the
ARR06 live-provider transcripts and human review.

## Validation strategy

- Focused Django tests for context, registry, executors, state sync, API and views.
- `scripts/ci_mobile_visual_check.sh tests/assistant-surface.test.ts` during iteration.
- `scripts/ci_mobile_iteration.sh` once after mobile stage closure.
- AI Assistant and relevant notas/mobile API suites before integration.
- Full repository gate once before merging.
- Real-provider and staging replays are different evidence and cannot be replaced by
  another execution of the fake-provider suite.

## Closure criteria

1. One canonical memory vocabulary is executable across context, tools and chat state.
2. Profile and saved-preference reads are visible in the intake tool set.
3. Preference writes are durable only after trusted approval.
4. Web and mobile represent the same approval capability.
5. Every healthy turn exposes a bounded outcome state.
6. The five real-provider scenarios pass in staging with human-reviewed transcripts.
