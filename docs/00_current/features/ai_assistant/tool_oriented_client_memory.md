# AI Assistant Tool-Oriented Client Memory

Status: current
Last updated: 2026-07-13
Audience: developers and AI assistants working on My Scoope AI workflows

## Purpose

This document is the current implementation contract promoted from the CM00-CM13 AI Assistant Client Memory & Profile Objects cycle.

The assistant should be treated as a product operator over My Scoope capabilities. It should help the user perform real product actions through allowlisted tools, typed draft objects, visible cards and explicit approval boundaries.

## Core model

```text
User language
  -> LLM assistant interprets intent and facts
  -> My Scoope tools receive typed inputs
  -> My Scoope validates and returns structured objects/cards
  -> Chat renders visible product objects
  -> Persistent writes require explicit user approval
```

The LLM is not a passive text rewriter and should not be reduced to prompt-only slot capture. It may interpret user intent, complete drafts and request reviewable product actions through tools.

My Scoope remains responsible for validation, rendering, persistence, permissions and safety boundaries.

## LLM freedom through tool contracts

Do not over-structure the assistant with long prompt prohibitions, deterministic questionnaire order or regex-style conversational guards. That pattern makes the product feel robotic and creates competing sources of truth.

The preferred boundary is:

```text
LLM interprets and asks naturally
  -> tools receive normalized, typed fields
  -> My Scoope validates and synchronizes state
  -> UI renders objects/cards
  -> persistence requires approval
```

Tool schemas and field descriptions should be clear enough for the LLM, MCP clients or future AI agents to use the capability directly. The backend validates values; it should not act as a parallel conversational interpreter in LLM mode except for technical fallback/deterministic mode.

Internal bookkeeping fields should not be framed as user-facing missing facts. For example, when the user provides a weight in chat, treat it as the current weight for the current proposal unless the user expresses uncertainty or requests historical tracking; do not ask for the weight source/date as a required intake step.

## Information objects

The assistant-facing memory model is intentionally split into visible objects.

| Object | Purpose | Persistence posture |
| --- | --- | --- |
| `profile_draft` | Physical/profile calculation context such as weight, height, age snapshot, sex, activity and training frequency. | Conversation-scoped until committed through approved profile update flow. |
| `preference_draft` | Food preferences, restrictions, avoided/preferred foods, dietary pattern and organization preferences. | Draft-only for now; reusable preference persistence requires a future approval flow. |
| `proposal_preferences` | Parameters for the current proposal such as goal, meals for this proposal, energy adjustment and optional targets. | Proposal-scoped by default. |
| `saved_comparison` | Existing saved comparison snapshots owned by the user. | Read-only through assistant tools. |
| `NutritionProposal` | Reviewable proposal created by product services. | Reviewable artifact; final application remains a separate approved action. |

`meals_per_day` must not be treated as a fixed personal profile field. It belongs to proposal preferences by default and may later be reusable as a soft meal-organization preference.

## Tool families now available

### Profile/client memory tools

```text
read_user_profile_context
update_profile_draft
share_profile_draft_card
commit_profile_update
```

`commit_profile_update` is an internal approval-only tool. It is not exposed to the LLM provider. It can persist only currently supported fields after trusted UI approval:

```text
weight_kg -> WeightLog
height_cm -> Profile.height_cm
sex -> Profile.sex
```

### Preference draft tools

```text
update_preference_draft
share_preference_draft_card
```

These are draft-only. They help the assistant capture preferences and restrictions without silently creating permanent memory.

### Proposal preference and proposal tools

```text
update_proposal_preferences
share_proposal_preferences_card
create_nutrition_engine_dailyplan_proposal_from_drafts
```

`create_nutrition_engine_dailyplan_proposal_from_drafts` composes `profile_draft`, `preference_draft` and `proposal_preferences` into an internal `NutritionBrief`, then uses the existing proposal engine to create a reviewable `NutritionProposal`.

### Comparison and validation tools

```text
compare_dailyplan_to_targets
list_saved_comparisons
read_saved_comparison
```

These are read-only or validation-only. They let the assistant use real comparison capabilities instead of speaking about comparisons abstractly.

### Existing read-only context tools

```text
list_user_proposals
read_dailyplan
read_proposal
search_operational_foods
list_operational_foods
```

## Conversation rules

The assistant should:

- receive greetings naturally when the user creates space for it;
- ask what the user needs before assuming a proposal flow;
- decide the next visible question itself in LLM modes, without deterministic suggested-question metadata;
- call `read_user_profile_context` when the user asks to use their ficha/profile/personal data;
- use tools when the user gives profile facts, food preferences, proposal preferences, comparison requests or proposal requests;
- show object cards when structured memory matters, without treating every draft update as a presentation event;
- avoid repeating fields already captured by tools;
- distinguish conversation/proposal use from persistent profile updates;
- keep persistent writes behind explicit user approval;
- explain results in human language after using product tools.

The assistant should avoid phrases that make the user feel like an interruption or a survey target, such as:

```text
me falta solo
sin hacerte perder tiempo
un dato de contexto
```

## Draft update and card presentation boundary

Updating memory for the current conversation is not the same action as presenting an object to the user.

```text
update_profile_draft / update_preference_draft / update_proposal_preferences
  -> silent state update
  -> no automatic card

read_user_profile_context / share_*_card
  -> explicit presentation result
  -> card may be appended to the chat
```

The initial profile card may be returned by `read_user_profile_context` when the user asks to use their ficha. Later partial facts should update the draft silently. A new card is appropriate when the user asks to review the object, after a meaningful grouped completion or before an approval/review step. It should not appear after every individual answer.

The chat renderer enforces this contract. Card payloads attached to update tools are ignored; only allowlisted card-producing tools may create visible chat objects.

## Field provenance

Drafts retain local `field_sources` maps. Once synchronized into `NutritionBrief`, provenance uses one canonical flat map keyed by the final brief field name. It covers profile facts, proposal parameters and mapped preference fields, and must survive serialization between turns.

This is intentionally not split into three parallel source structures. The draft namespace explains where the value originated before synchronization; the canonical brief field explains what the value means after synchronization.

## Provider context boundary

For LLM nutrition intake, provider context should describe current product objects and capabilities rather than a second slot-completion policy.

The current `tool_oriented_intake.v8` payload exposes:

```text
current_drafts.profile_draft
current_drafts.preference_draft
current_drafts.proposal_preferences
optional work_context
concise context_semantics
```

Values present in those drafts are already known for the current conversation. An absent value is not automatically required; the assistant decides whether it is useful for the user's request. Field meanings, enums and normalization belong to the typed tool descriptions/schemas.

The provider context must not duplicate those objects through `known_fields`, `do_not_ask_again_fields`, completeness policies, recommended tool sequences or a second raw `nutrition_brief` in the intake surface. Recent cards expose their visible state so references can be resolved, but they do not contain instructions that choose the next question.

The generic sanitizer must preserve bounded drafts, provenance maps, recent messages and chat objects while continuing to remove sensitive keys and truncate oversized content.

## Prompt and response-policy boundary

Provider prompts define the assistant's role, grounding, safety and response quality. They must not define a mandatory intake order or a universal number of questions per turn.

```text
zero questions       -> valid when the request can be answered or acted on
one question         -> valid when one clarification is useful
several questions    -> valid when closely related and more natural together
```

The assistant should adapt to the user's message, use known context and ask only when ambiguity materially affects the answer or product action. Missing optional fields do not create an automatic interview backlog.

Field meanings, enums, normalization examples and object scope belong to typed tool descriptions/schemas. Prompt-level policy should not duplicate rules such as which exact draft receives goal, weight or meal-count data.

Legacy deterministic question selection remains available for deterministic/fallback paths only. It is not provider-facing policy in LLM mode.

## Deterministic runtime isolation

Deterministic conversation behavior is an explicit engine, not a shared policy layer inside LLM turns.

```text
deterministic_chat_engine.py
  -> semantic extraction and contextual short-answer parsing
  -> pending_field
  -> deterministic question/acknowledgement copy

LLM chat engines
  -> provider interpretation
  -> typed tool calls and tool-result state synchronization
  -> cards, provenance and proposal readiness
  -> no backend-owned next question
```

LLM state uses `build_llm_intake_result_from_brief()`. It intentionally exposes no `pending_field`, `follow_up_questions`, `required_follow_up_questions` or `visible_follow_up_questions`. Missing proposal inputs are still validated by `required_proposal_fields()`, a technical field-level contract without user-visible wording.

A provider failure returns a technical fallback message and does not run the deterministic parser for the same message. The deterministic engine may be selected only by explicit engine configuration or by a production rollout decision that routes the entire turn to that engine. Runtime metadata must report the selected `conversation_policy`, fallback kind and whether the deterministic runtime was invoked.

Regex-based tone rewriting, repeated-question phrase guards and local conversational acknowledgements do not belong in LLM runtime. Technical output extraction, JSON-envelope protection, bounded normalization and server-side proposal validation remain valid shared safeguards.

## Replay invariant boundary

Fake-provider replays protect product behavior without requiring a single valid question order. Each scenario may vary phrasing, group several facts in one message, omit optional details or change direction.

The durable replay contract is:

```text
state survives later turns
known facts do not return as missing
update tools stay silent
read/share tools own cards
provider JSON stays invisible
profile and final nutrition objects are not mutated by drafts
real proposals remain reviewable until explicit apply
```

Tests should assert these outcomes and tool/persistence boundaries. They should not depend on fixed turn numbers unless the turn number itself is the behavior being protected.

## State synchronization rule

Tool results that update draft objects must be synchronized back into the conversation-scoped `NutritionBrief` when supported. Cards, follow-up questions and proposal readiness should read the same temporary state.

In LLM-led runtime, deterministic intake questions are not provider instructions. The provider receives current drafts and tools; the LLM decides the next question and records facts through tools.

If the user chooses their ficha, `read_user_profile_context` should return a conversation draft/card and a source patch so `subject_source` is remembered without asking again.

## Approval boundary

Draft tools can complete temporary objects from natural language. They must not persist durable user memory.

Persistent profile or future preference updates require:

```text
trusted UI action
explicit approval metadata
server-side validation
bounded commit tool
```

The LLM provider must not be able to call final write tools directly.

## Test posture

Changes to this area should run at minimum:

```bash
python manage.py check
python manage.py test ai_assistant   notas.tests.test_ai_profile_tools   notas.tests.test_ai_preference_tools   notas.tests.test_ai_proposal_preference_tools   notas.tests.test_ai_proposal_from_draft_tools   notas.tests.test_ai_tool_results   notas.tests.test_ai_intake_llm_profile_cards   notas.tests.test_ai_intake_ai_assistant_cards   notas.tests.test_ai_comparison_tools   notas.tests.test_ai_intake_llm_tool_state_sync   notas.tests.test_ai_intake_tool_led_regressions -v 1
```

Use the full test suite before merging broad changes when dependencies and time allow.

## Open follow-up work

The CM00-CM13 cycle closes the tool-oriented client-memory baseline. Future cycles may address:

- persistent food/preference memory models with approval flows;
- richer body-state history for activity and training;
- final proposal apply/update tools;
- saved comparison card rendering in the chat thread;
- broader end-to-end conversation tests with live/stubbed provider behavior;
- improved UI affordances for editing and reviewing remembered information.

## Real-provider validation gate

Fake-provider replays protect deterministic system invariants, but they do not prove the UX quality of the configured model. CM24 adds a controlled staging command:

```bash
python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email <staging-user-email> \
  --output artifacts/local/cm24_real_provider_report.json \
  --fail-on-hard-regression
```

The command uses synthetic turns, disables reviewable proposal tools and does not persist chat history, profile changes or final nutrition objects. Real provider usage, `AIUsageEvent` records and credits remain active and attributable through `assistant.ai_nutrition_intake.cm24_validation`.

The chat-engine metadata exposes only the bounded values required for diagnostics:

```text
llm_semantic_intent
llm_semantic_missing_slots
llm_tool_results[{tool_name, status, error_code?}]
```

It must not expose tool payload data, error messages, provider raw responses or secrets.

Automated validation checks visible-text boundaries, LLM-only execution, grouped-fact state, intent transitions, repeated missing slots, tool contracts, card pacing and usage events. `AIUsageEvent` is the authoritative hard evidence for provider execution; safe chat metadata mirrors provider/model/usage for diagnostics.

Visible text is not state. When the assistant claims that a profile fact, preference, proposal direction or real object was read, registered, changed or will be used, the same turn must request the matching typed tool. Explicit card-review requests require `share_*_card`; a plain-text list is not a card.

Transcript naturalness and usefulness remain a required human review. The LLM-native alignment cycle closes only after both gates pass.

## Native provider function-call transport

The OpenAI adapter exposes allowlisted My Scoope capabilities as provider-native custom functions. Tool names and arguments no longer live inside the assistant JSON envelope. OpenAI emits `function_call` items; My Scoope validates and executes them through the existing tool registry and returns sanitized `function_call_output` items.

`ai_assistant_structured_response.v2` remains provider-enforced for the smaller visible response: assistant copy, semantic intent and `requires_human_review`. This prevents tool payloads from competing with visible text for the same nested JSON output.

The flow remains stateless with `store=false`. Bounded provider continuation items, including encrypted reasoning content when returned, are supplied again with function outputs. My Scoope still owns tool limits, permissions, draft/write boundaries and card rendering.

A malformed/incomplete final text envelope, or an initial operational response without a native function call, may receive one bounded repair attempt. LLM turns still do not invoke the deterministic intake parser. The ordinary product output cap remains 900 tokens; CM24 live validation uses its bounded diagnostic configuration.

`complexity_level` is part of proposal preferences, not personal memory. The update tool normalizes user language into `low`, `medium` or `high` and synchronizes the value into `NutritionBrief`. If a provider-native tool has already returned a typed result but the post-tool provider continuation fails, the runtime may present a minimal local acknowledgement derived only from that result while preserving the native-call evidence and degradation metadata. This acknowledgement uses policy `state_ack_only.v2`: it cannot choose the next question, append a profile-source prompt or infer a missing-field agenda. Its usage event is `degraded`, and any occurrence blocks the real-provider release gate instead of masquerading as a healthy turn.
The native function schema exposes `complexity_level` and the other proposal fields as real nested properties under `updates`. A generic object plus a prose field list is insufficient for the CM24 contract: the provider may understand “simple” in visible text yet omit it from function arguments. The schema remains compact and server-side normalization remains authoritative.
The OpenAI-facing `update_proposal_preferences` declaration is strict and nullable. Every proposal field is required by the function schema, but fields absent from the user's turn are emitted as `null` and removed before My Scoope validation. Separately, the provider receives only tools executable under the current runtime flags; disabling reviewable proposal tools removes those schemas rather than merely blocking them after selection.
The draft-to-brief projector must copy every canonical proposal field present in a successful tool result. In particular, `complexity_level` must survive the `proposal_preferences` -> `NutritionBrief` boundary with its field source; cards are not evidence that state synchronization succeeded.
