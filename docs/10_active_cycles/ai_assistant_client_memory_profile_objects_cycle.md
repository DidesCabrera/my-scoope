# AI Assistant Client Memory & Profile Objects Cycle

Status: active alignment extension (CM00-CM13 baseline completed)
Date: 2026-07-09
Completed: 2026-07-10
Owner: Product / AI Assistant / Nutrition UX
App targets: `ai_assistant`, `notas`, future profile/preference services
Related areas: onboarding nutrition profile, proposals, comparators, nutrition solver
Related decisions: `0085-ai-assistant-client-memory-profile-objects.md`, `0086-ai-assistant-tool-oriented-operator.md`, `0098-ai-assistant-client-memory-cycle-closure.md`

## Context

The first LLM preview conversations showed an important product issue: improving tone, bullets or JSON parsing is not enough if the assistant cannot preserve user context reliably.

Observed symptoms:

```text
- the assistant can say it understood a goal, but ask for it again later;
- it can accept personal profile usage, but reopen the same decision;
- it can capture height or activity in visible text, but fail to persist that fact in the internal brief;
- it can sound like a form or survey instead of a respectful assistant;
- the user cannot clearly see what My Scoope remembers, what is temporary and what still needs approval.
```

During early CM patches, another issue became clear: a deterministic intake layer and an LLM response layer can become two competing brains. If one part owns state and another part decides visible questions, the user experiences an assistant that appears to understand but forgets.

This cycle therefore moves toward a tool-oriented assistant model.

## Product thesis

```text
A good assistant does not only answer.
A good assistant helps the user operate the product through real capabilities.
```

For My Scoope this means:

```text
The LLM is the user-facing assistant and interpreter.
My Scoope provides typed tools, schemas, cards and approval boundaries.
The UI shows memory as objects the user can inspect.
Persistent changes require explicit user approval.
```

The assistant should not be reduced to a decorative text rewriter. It should be allowed to understand the user, complete drafts and request actions through product tools. At the same time, it must not silently mutate persistent profile or preference data.

## Role of the AI Assistant

The AI Assistant is a product operator over My Scoope capabilities.

It should help the user do things that the product already supports, or that the product exposes through safe tools:

```text
- create nutrition proposals;
- compare plans or proposals;
- read and use the user's profile context;
- prepare profile or preference drafts;
- show reviewable cards;
- request approval for persistent updates;
- explain results and guide next steps.
```

The LLM should not invent capabilities that do not exist. When a capability is needed, the product should expose it as an explicit tool with a typed contract, permission boundary and UI consequence.

## UX target

The target conversation should be organized by user intent and visible objects, not by raw missing slots.

### 1. Reception / greeting space

If the user opens with a greeting or asks how the assistant is, the assistant should briefly reciprocate before asking what the user needs.

Example direction:

```text
¡Hola! Muy bien, gracias. ¿Y tú, cómo estás?

Cuéntame, ¿en qué puedo ayudarte hoy?
```

The assistant should not assume the user wants a nutrition proposal just because the user greeted it.

### 2. Work indication

The assistant should identify the requested work type:

```text
proposal
comparison
consultation
review_existing_plan
modify_existing_entity
unknown
```

The first open question should be general, not proposal-specific:

```text
¿En qué puedo ayudarte hoy?
```

or a natural variant.

### 3. Tool-backed work

When the work type is known, the assistant should use the relevant tool family instead of free-form guessing.

Examples:

```text
Proposal requested -> proposal/profile/preference tools
Comparison requested -> comparator tools
Profile update requested -> profile draft and approval tools
Food preference detected -> preference draft tools
```

This preserves the assistant role while keeping actions grounded in product capabilities.

### 4. Proposal subject decision

If the work is a nutrition proposal, the assistant should determine the subject of calculation:

```text
self_profile
external_chat_data
manual_chat_data
unknown
```

If the user already said “usa mi ficha” or “es para mí”, this decision should be captured through the relevant draft/tool contract and not asked again.

### 5. Profile object visibility

When the user chooses to use their personal profile, the assistant should not ask isolated fields blindly. It should use/read a profile context tool and show a profile card/component with present and missing data.

Conceptual UI card:

```text
Ficha personal usada para esta propuesta

Datos base
- Edad: 38 años
- Sexo nutricional: masculino
- Altura: pendiente

Estado físico
- Peso actual: 88 kg
- Actividad: pendiente

Preferencias
- Patrón alimentario: pendiente
- Alimentos evitados: pendiente
```

This lets the user understand what the system remembers and what is still missing.

### 6. Draft-first completion

When the user provides missing data in chat, the assistant should complete a draft object through a tool:

```text
profile_draft
preference_draft
proposal_preferences
```

The assistant can then send an updated card with an explicit action:

```text
Actualizar ficha personal
```

Persistent profile updates require user approval. Until approved, the values may be used as temporary conversation/proposal context only.

## Information objects

The cycle separates user information into explicit objects.

### Personal base profile

Relatively stable calculation data.

```text
birth_date or age snapshot
sex_for_calculation
height_cm
```

These are relevant for nutrition calculations and should be visible in the user profile UI. Updates should be deliberate.

### Body state

Body and activity information that changes over time.

```text
current_weight_kg
weight_source
weight_recorded_at
activity_level
training_frequency
training_type
```

Weight should continue to respect `WeightLog` / Body Metrics direction instead of becoming a single mutable scalar with no history.

### Food preference profile

Food restrictions and preferences that improve adherence.

```text
dietary_pattern
avoided_foods
preferred_foods
allergies_or_intolerances
preferred_food_categories
disliked_food_categories
```

These should be treated differently by optimization logic depending on strength:

```text
hard restriction: vegan, allergy, declared no-consumption
soft preference: prefers chicken, dislikes tuna, wants simpler meals
```

### Meal organization preferences

How the user prefers to structure eating.

```text
preferred_meals_per_day
usual_meal_times
cooking_time_preference
budget_preference
simplicity_preference
variety_preference
```

`preferred_meals_per_day` may be useful as a preference, but the number of meals for a specific proposal is primarily a proposal parameter and can change often.

### Proposal draft

Temporary information for the current work.

```text
goal
proposal_meals_per_day
constraints_snapshot
profile_snapshot_used
preference_snapshot_used
calorie_strategy
macro_strategy
```

The proposal draft should be allowed to differ from the persistent profile.

### Pending assistant memory

Facts detected by the assistant but not yet persisted.

```text
pending_profile_updates
pending_preference_updates
pending_proposal_preferences
source_message_id
confidence
requires_user_approval
```

This prevents invisible memory and lets the user approve, correct or discard what the assistant learned.

## Tool families

The assistant should use tools grouped by product capability.

### Profile and client memory tools

```text
read_user_profile_context
update_profile_draft
share_profile_card
propose_profile_update
commit_profile_update_after_approval
```

Purpose: let the assistant understand and complete profile-related information without silently mutating persistent data.

### Preference tools

```text
read_user_preference_context
update_food_preference_draft
update_meal_organization_draft
share_preference_card
commit_preference_update_after_approval
```

Purpose: let the assistant learn food restrictions, preferred foods, avoided foods and meal organization preferences as visible, approvable memory.

### Proposal tools

```text
update_proposal_preferences
create_nutrition_proposal
share_proposal_card
```

Purpose: create proposals from explicit profile/preference snapshots and proposal-scoped preferences.

### Comparator tools

```text
list_comparable_plans_or_proposals
compare_plan_to_plan
compare_proposal_to_targets
share_comparison_card
```

Purpose: expose existing comparison capabilities to the assistant instead of making it speak about comparisons abstractly.

### Read-only context tools

```text
list_user_proposals
read_dailyplan
read_proposal
list_food_catalog
```

Purpose: let the assistant ground explanations and actions in real user/system data.

## Tool design rules

Tools are the contract between the LLM and My Scoope.

A tool should define:

```text
name
purpose
input schema
output schema
read/write level
approval requirement
allowed side effects
UI component result, if any
error modes
observability event
```

Write tools should prefer draft-first behavior. Final writes require explicit approval unless the action is already clearly reviewable and reversible.

## Stability and relevance matrix

| Information type | Examples | Stability | Relevance for optimizer | Persistence rule |
| --- | --- | --- | --- | --- |
| Base profile | height, sex, birth date | high | high | persist with explicit update |
| Body state | weight, activity, training | medium | high | use logs/snapshots; approve defaults |
| Food restrictions | vegan, allergy, avoided foods | medium/high | high | approve before persistent use |
| Food preferences | preferred foods, disliked foods | medium | medium/high | draft first, approve if reusable |
| Meal organization | meals/day, timings, prep style | low/medium | medium | proposal-scoped by default |
| Goal | gain mass, lose fat, maintain | variable | high | proposal-scoped unless promoted |

## Responsibility boundaries

### `ai_assistant`

Owns conversational policy, structured output contracts, tool schemas, tool orchestration, provider gateway and safe interpretation of user language.

It should expose system capabilities to the LLM through tools. It should not directly mutate persistent profile/preference models outside approved tool boundaries.

### `notas`

Currently owns operational nutrition entities, profile data and `AiNutritionChat` UI integration while extraction continues.

It can host the chat surface, conversation records and initial card rendering, but reusable memory/tool contracts should move toward explicit application services.

### `accounts`

Owns account/onboarding entrypoints and commercial entitlements. It should not become the owner of all nutrition preference state by default.

### `nutrition_solver`

Consumes explicit calculation context and constraints. It should not infer user memory from chat text.

### Future preference/profile services

As the product matures, profile and preference memory may deserve dedicated services or models separate from legacy `Profile`.

## State and tool direction

The next implementation cycle should move from loose chat memory toward LLM-led tool use with explicit state objects:

```text
work_intent
active_object
profile_snapshot
profile_draft
preference_draft
proposal_preferences
pending_approval_actions
visible_ui_components
tool_results
```

Core rule:

```text
The LLM assists and fills drafts through tools.
My Scoope validates tool inputs, renders tool outputs and controls persistence.
```

The system should not run a parallel deterministic interviewer that asks a different question from the LLM. If a deterministic fallback exists, it must share the same tool/state contract.

## Conversation rules

The assistant should:

- receive greetings naturally when the user gives space for that;
- ask one main question at a time unless a visible card clearly asks for a grouped set of missing fields;
- avoid sounding rushed or like a street survey;
- avoid phrases like “me falta solo”, “sin hacerte perder tiempo” or “un dato de contexto”;
- not repeat fields already captured in draft, profile or proposal state;
- expose remembered information through UI cards when it matters;
- distinguish “use for this proposal” from “save to my profile”;
- use product tools when the user asks to do something My Scoope can do.

## Proposed patch cycle

```text
CM00 — Docs: Client memory and profile objects cycle
CM01 — Decision: AI Assistant as tool-oriented product operator
CM02 — Tool contract inventory for profile, preferences, proposals and comparisons
CM03 — Profile context/read tool and profile draft update tool — implemented
CM04 — Profile card tool result rendered inside the chat thread — implemented
CM05 — Approval tool for committing profile updates after user confirmation — implemented
CM06 — Food and meal preference draft tools — implemented
CM07 — Proposal preference and proposal creation tool alignment — implemented
CM08 — Comparator tools exposed to the assistant — implemented
CM09 — LLM tool-loop integration for profile/preference/proposal flows — implemented
CM10 — Proposal generation from draft objects — implemented
CM11 — Tool-oriented intake context and policy cleanup — implemented
CM12 — Regression tests for tool-led memory, no-repeat behavior and approval boundaries — implemented
CM13 — Cycle closure and current docs promotion — implemented
```


### CM03 — Profile context/read tool and profile draft update tool — implemented

CM03 adds the first profile-memory tools to the AI Assistant tool system:

```text
read_user_profile_context
update_profile_draft
share_profile_draft_card
```

The implementation keeps the assistant aligned with the product-operator model:

```text
LLM understands user facts and calls tools.
Tools validate and return profile draft/card payloads.
Persistent ficha updates remain disabled until an explicit approval/commit tool exists.
```

It also introduces the `draft` tool category for non-persistent structured state changes. Draft tools are not plain reads, but they are not writes to permanent product data.

CM04 connects profile draft tool outputs to chat cards. Follow-up CM05 should add the explicit approval/commit flow instead of letting the LLM or a draft tool persist ficha changes directly.



### CM04 — Profile card tool result rendered inside the chat thread — implemented

CM04 connects profile draft tool outputs to the visible chat UI. `update_profile_draft` now returns both the structured draft and a renderable `profile_draft_card`; the nutrition chat adapter appends that card as an assistant message in the thread when it comes from a controlled tool result.

This means profile memory is no longer only prose generated by the LLM. It is a My Scoope object shown in the conversation, following the same UX principle as proposal cards. Duplicate cards are suppressed, and persistent ficha updates remain outside draft tools until CM05.



### CM05 — Approval tool for committing profile updates after user confirmation — implemented

CM05 adds `commit_profile_update` as an internal commit tool. It is registered in the AI Assistant tool registry but is not exposed to the LLM provider. Execution requires trusted server-side approval metadata from the profile card UI, so the model cannot persist user profile data by simply asking for a write tool.

The tool persists only fields supported by the current ficha/body metrics model:

```text
weight_kg -> WeightLog
height_cm -> Profile.height_cm
sex -> Profile.sex
```

Age, activity and training frequency remain conversation/proposal context until dedicated profile/body-state/preference objects exist. This keeps the cycle aligned with the user-visible memory principle: drafts may be completed conversationally, but persistent memory is approved and bounded.



### CM07 — Proposal preference and proposal creation tool alignment — implemented

CM07 adds proposal-scoped draft tools:

```text
update_proposal_preferences
share_proposal_preferences_card
```

These tools let the LLM capture the current proposal direction without mixing it into the personal ficha or reusable food-preference memory. The object covers goal, requested entity, meal count for this proposal, energy adjustment, optional macro targets and notes.

The tool result includes a `proposal_preferences_card`, rendered as a chat-thread object. This keeps the UI separation visible:

```text
profile_draft          -> body/profile calculation context
preference_draft       -> food and meal-organization preferences
proposal_preferences   -> parameters for this proposal only
```

Future proposal creation should assemble a `NutritionBrief` from these explicit tool outputs rather than relying on a parallel deterministic interviewer.

## Non-goals for the first implementation patch

Do not immediately implement all persistent preference models.

### CM06 — Food and meal preference draft tools — implemented

CM06 adds provider-exposed draft tools for preference memory:

```text
update_preference_draft
share_preference_draft_card
```

These tools let the LLM act as an assistant: it can interpret natural language such as avoided foods, preferred foods, dietary pattern, allergies/intolerances, preferred meal count, budget, simplicity, variety and cooking-time preferences, then complete a structured `preference_draft`.

The draft is separate from the body/profile ficha. It may be rendered as a chat card, but it does not persist anything yet. Persistent preference memory remains a future approval flow.


Do not let the LLM directly update persistent profile data without a tool contract and approval boundary.

Do not collapse all information into a single flat `Profile` object.

Do not make `number_of_meals` a required permanent personal profile field.

Do not replace the existing chat UI with a parallel assistant UI.

Do not keep adding prompt-only fixes for memory behavior when the missing capability is a product tool.

## Success criteria

The cycle succeeds when:

```text
- the user can see what My Scoope knows/remembers about them;
- the assistant can complete drafts from natural language through tools;
- the assistant does not ask again for data already captured;
- profile data, preferences and proposal parameters are visually distinct;
- persistent updates require explicit user approval;
- comparisons and proposals use real product capabilities through tools;
- proposal generation receives an explicit subject/preference snapshot.
```



### CM08 — Comparator tools exposed to the assistant — implemented

CM08 adds read-only saved-comparison tools:

```text
list_saved_comparisons
read_saved_comparison
```

This complements the existing `compare_dailyplan_to_targets` validation tool. The assistant can now inspect real `SavedComparison` records owned by the user, using snapshot payloads when available. The tools are read-only, owner-scoped and return a `saved_comparison_card` payload for future chat rendering.

This keeps comparisons aligned with the tool-oriented assistant model: the LLM does not invent comparisons; it reads existing product comparison objects through safe contracts.

### CM09 — LLM tool-loop integration for profile/preference/proposal flows — implemented

CM09 closes the gap between controlled tool outputs and the legacy nutrition chat state. When the LLM calls draft tools successfully, My Scoope now folds supported tool result objects back into the conversation-scoped `NutritionBrief`:

```text
profile_draft
preference_draft
proposal_preferences
nutrition_brief_patch
```

This does not persist user data. It keeps the current chat/proposal flow aligned with tool-led memory so cards, follow-up questions and proposal readiness read the same temporary state. Persistent ficha/preference updates still require explicit approval tools.

The key UX effect is that if a tool captures height, objective, foods to avoid or proposal meal count, the next turn should not behave as if those facts were only visual text in a card.


### CM10 — Proposal generation from draft objects — implemented

CM10 adds a reviewable proposal tool:

```text
create_nutrition_engine_dailyplan_proposal_from_drafts
```

The tool lets the LLM operate as an assistant over the objects introduced earlier in the cycle:

```text
profile_draft
preference_draft
proposal_preferences
```

My Scoope composes those objects into the internal `NutritionBrief` contract and then uses the existing nutrition engine proposal flow. The result is still a reviewable `NutritionProposal`; no final DailyPlan is applied, and no profile or preference memory is persisted.

This closes the main product loop for the tool-oriented intake: the assistant can collect user context through tools and request a real proposal through a controlled product capability instead of relying on prose or a parallel deterministic interviewer.

### CM11 — Tool-oriented intake context and policy cleanup — implemented

CM11 clarifies the provider-facing operating model after the tool families are available. The LLM should behave as an assistant/operator over My Scoope capabilities, not as a plain text chatbot and not as a second deterministic interviewer.

The safe context for `ai_nutrition_intake` now exposes:

```text
metadata.tool_oriented_intake.current_drafts.profile_draft
metadata.tool_oriented_intake.current_drafts.preference_draft
metadata.tool_oriented_intake.current_drafts.proposal_preferences
metadata.tool_oriented_intake.recommended_tool_sequence
```

This tells the LLM which structured objects already exist in the current conversation and which tools should be used when the user gives new facts. The provider context also reflects whether reviewable proposal tools are enabled through `AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS`.

Historical note: CM20 supersedes the `recommended_tool_sequence` part of this CM11 payload. Current drafts remain provider-facing, while tool selection now comes from the allowlisted typed tool declarations.

The key rule is now explicit:

```text
The LLM can interpret and assist, but durable conversation memory must be represented through My Scoope draft tools and tool results.
```

This patch does not remove the legacy deterministic state bridge yet. It narrows its role and makes the provider-facing contract match the cycle thesis: tool-led assistance over visible product objects.

### CM12 — Regression tests for tool-led memory, no-repeat behavior and approval boundaries — implemented

CM12 adds regression coverage for the most important UX boundary in the tool-oriented assistant model: when a tool captures a fact, the visible assistant reply must not ask for that same fact again.

The nutrition intake LLM adapter now runs a post-tool visible-text guard after tool results are synchronized into the conversation-scoped `NutritionBrief`. If the provider asks for a known field after the tool loop, My Scoope replaces the visible text with a neutral acknowledgement and records guard metadata.

The tests cover:

```text
- provider asks for a goal after `update_proposal_preferences` captured it;
- profile, preference and proposal-preference tool results update the same temporary brief in one turn;
- draft tool results remain non-persistent and preserve the approval boundary.
```

This keeps the LLM in the assistant/operator role while ensuring user-visible text cannot contradict controlled tool state.


## CM13 — Cycle closure and current docs promotion — implemented

CM13 closes the active cycle and promotes the durable contract to current docs:

```text
docs/00_current/features/ai_assistant/tool_oriented_client_memory.md
```

The cycle is considered complete because the assistant now has a coherent tool-oriented baseline:

```text
- profile/client-memory draft tools;
- profile card rendering from controlled tool results;
- internal approval-only commit tool for supported profile fields;
- preference draft tools;
- proposal-preference draft tools;
- saved-comparison read tools;
- proposal creation from draft objects;
- tool-result synchronization into temporary chat state;
- provider-facing tool-oriented context;
- regression tests for no-repeat behavior and approval boundaries.
```

This does not mean client memory is complete as a product area. It means the architectural baseline is now stable enough to leave `docs/10_active_cycles/` as a completed cycle and let future work happen as smaller cycles: persistent preferences, richer body-state memory, final apply/update tools, comparison cards and broader end-to-end UX tests.

## Closure criteria

The cycle closes with these accepted rules:

```text
The LLM is the assistant/operator.
My Scoope exposes product capabilities as tools.
Draft objects are visible and conversation-scoped by default.
Cards are product objects, not decorative prose.
Persistent writes require explicit user approval.
Tool results must synchronize with temporary chat state.
Regression tests must protect no-repeat behavior.
```
## Post-closure diagnostic hotfixes

### CM17 — Conversation debug harness and visible-text boundary

CM17 adds `debug_ai_assistant_conversation`, a management command for replaying assistant turns with safe metadata, tool results, state snapshots and optional raw provider responses. It also reinforces the chat UI boundary so raw structured provider envelopes cannot be persisted as visible chat text; only `assistant_message.content` may reach the user bubble.

### CM18 — Scripted replay scenarios with fake provider

CM18 turns the debug harness into a reusable pre-UI validation path. It adds scripted fake-provider scenarios that run through the real AI Assistant runtime: provider JSON parsing, tool execution, tool-result state sync, card rendering and final visible text.

This protects the system from regressions that browser testing previously exposed late, especially raw JSON leakage, state/card divergence and blank assistant text after card-only messages.

The first built-in scenarios are:

```text
dieta_con_ficha_tool_led
json_visible_boundary
```

Future AI Assistant behavior patches should pass these scenario replays before being handed to manual real-provider testing.

## LLM-native alignment extension

Status: active
Started: 2026-07-13

The CM00-CM13 baseline established the correct product architecture, and CM17-CM18 added diagnostic coverage. Real conversations and replay inspection then showed that parts of the implementation still encoded the previous questionnaire mindset.

The purpose of this extension is not to give the LLM fewer boundaries. It is to move structure to the correct boundaries:

```text
clear role
+ typed tools
+ current objects
+ validation
+ permissions
+ observability

instead of

fixed conversational sequence
+ duplicated missing-field policy
+ automatic presentation side effects
+ semantic parsers competing with the LLM
```

### CM19 — Silent draft updates and explicit card sharing — implemented

CM19 separates object mutation from object presentation across profile, preference and proposal-preference drafts.

```text
update_*              -> update temporary state silently
read profile context  -> may show the initial ficha card
share_*_card          -> deliberately show a reviewable object
```

The chat adapter only accepts cards from explicit card-producing tools. This protects the UX even if an old or malformed update result still contains a card payload.

CM19 also keeps `NutritionBrief.field_sources` as one canonical map but expands it beyond profile fields. Proposal and mapped preference provenance now survives serialization and later turns.

Accepted UX invariant:

```text
Initial ficha card: visible when the user requests their ficha.
Partial age/sex/activity answers: state updates, no repeated cards.
Meaningful completion or requested review: explicit share tool may show a new card.
```

Decision: `docs/20_decisions/0104-ai-assistant-draft-update-card-sharing-boundary.md`.

### CM20 — Provider context simplification — implemented

CM20 removes provider-facing structures that reconstructed a deterministic interviewer around the LLM. The intake payload now keeps current draft objects and concise capability/state semantics instead of duplicated completeness policy.

Removed from provider context:

```text
known_fields/do_not_ask_again_fields copies
profile_completion and missing-count policy
recommended_tool_sequence
long intake rules arrays
readiness/pending-question flags
card instructional_meaning
duplicated raw nutrition_brief beside current drafts
```

Kept:

```text
assistant role
recent conversation and visible object state
current profile/preference/proposal drafts
typed tool names, descriptions and schemas
runtime capability flags
persistence/safety boundaries
```

The provider sanitizer now preserves the bounded nested draft/card structures instead of truncating them before delivery. Sensitive-key filtering, text/list limits, backend validation and technical limits remain unchanged.

Decision: `docs/20_decisions/0105-ai-assistant-provider-context-simplification.md`.

### CM21 — Prompt and response-policy cleanup — implemented

CM21 removes the fixed intake order and universal one-question pacing from provider-facing system/developer prompts. The response policy now permits zero, one or several closely related questions according to the current turn, while discouraging mechanical questionnaires and artificial missing-data urgency.

```text
before: intention -> physical context -> activity -> plan shape
before: at most one visible question per turn
now:   answer / confirm / ask / group / use tools as the turn requires
```

Field-specific meanings, enums and normalization examples remain in typed tool descriptions and schemas. General prompt policy keeps only response quality, context continuity, grounding, review and safety boundaries.

Obsolete provider-facing intake-policy builders were removed from `conversational_intake.py`. Its remaining stage/question helpers were explicitly legacy deterministic fallback behavior and were not consumed by the provider runtime; CM23 later moved them into the isolated deterministic boundary.

The question formatter no longer carries a hidden global one-item default. Existing deterministic call sites that explicitly request one question retained their behavior and were isolated by CM23.

Decision: `docs/20_decisions/0106-ai-assistant-adaptive-prompt-response-policy.md`.

### CM22 — Invariant-based replay scenarios — implemented

CM22 replaces turn-index choreography assertions with a reusable invariant report. Scenarios declare final facts, stable captured fields, intentional transitions, tool/card expectations and persistence boundaries. The harness records provider exchanges, tool names and card deltas per user turn.

Protected invariants:

```text
captured facts survive later turns
known facts are not requested again as missing
updates do not automatically render cards
explicit read/share tools render cards
raw provider JSON never reaches visible text
profile, weight history and final nutrition objects remain unchanged
reviewable proposal creation is allowed only when explicitly expected
provider-callable final apply tools remain forbidden
```

Built-in replay variants now cover grouped facts in a single message, free-order capture, explicit changes of goal/requested entity, omitted optional preferences and the anti-JSON boundary. A database-backed replay invokes the real `create_validated_meal_proposal` tool and confirms that it creates only a pending-review `NutritionProposal`, not a final `Meal` or applied change.

The diagnostic command prints each invariant outcome and includes tools/card deltas in JSON output. Exact conversational wording or turn order is no longer treated as the product contract.

Decision: `docs/20_decisions/0107-ai-assistant-invariant-based-conversation-replays.md`.

### CM23 — Legacy deterministic boundary isolation — implemented

CM23 physically separates the explicit rule-based engine and its question-selection policy from the LLM runtime. `DeterministicNutritionIntakeChatEngine` now lives in `deterministic_chat_engine.py`; stage/question copy lives in `deterministic_policy.py`; the provider-adjacent legacy module was removed.

LLM turns and tool-result synchronization now use `build_llm_intake_result_from_brief()`, a state-only builder that preserves typed facts, cards, provenance and proposal readiness while clearing `pending_field` and every backend-generated follow-up-question list. Proposal readiness uses `required_proposal_fields()`, which returns canonical identifiers without visible conversational copy.

Provider failures return a bounded technical message and explicitly report `deterministic_runtime_invoked=false`. The deterministic engine is used only when configured directly or when production rollout intentionally selects it as the whole-turn fallback. Preview engines no longer instantiate a deterministic baseline eagerly.

Unused regex tone/repetition guards and local fallback acknowledgements were removed from the LLM chat module. The retained JSON-visible boundary and text/list normalization are technical safeguards, not conversation policy.

Accepted boundary:

```text
Deterministic mode -> semantic parsers + pending field + deterministic question selection.
LLM mode           -> LLM + tools + typed state/readiness; no backend-owned next question.
```

Decision: `docs/20_decisions/0108-ai-assistant-legacy-deterministic-boundary-isolation.md`.

### CM24 — Real-provider UX validation and alignment closure — harness implemented, live gate pending

CM24 adds `validate_ai_assistant_real_provider`, an explicit staging command that runs synthetic scenarios through the configured non-fake provider and produces a JSON evidence report. The command requires `--live`, one existing staging user and usage observability. It uses the LLM preview runtime directly and disables reviewable proposal tools, so validation can exercise drafts, reads, cards, readiness and tool-error recovery without creating proposals or final nutrition entities.

The built-in suite evaluates:

```text
natural greeting and task discovery
no unnecessary repeated questions
card pacing
multi-fact capture
changes of intent
proposal readiness
tool errors and recovery
visible-text quality
credit/usage observability
```

Automated hard invariants cover provider/fallback identity, visible-text boundaries, typed brief state, known fields reintroduced as missing, tool results, card deltas and persisted usage events. Bounded engine metadata exposes semantic intent, missing slots and tool name/status/error code only; tool data and raw provider responses remain excluded.

Naturalness, acknowledgement quality and overall usefulness remain a human gate. The report therefore always declares `manual_review_required=true`.

Runbook: `docs/40_technical/qa/ai_assistant_real_provider_validation.md`.
Decision: `docs/20_decisions/0109-ai-assistant-real-provider-ux-validation-gate.md`.

Closure condition:

```text
fake-provider invariant suite passes
+ one complete live staging report has no hard regressions
+ every transcript receives a human disposition
+ remaining product work is moved to separate cycles/issues
```

Until that evidence exists, CM24 is implemented but the alignment extension is not represented as completed.

#### First live run and CM24 calibration hotfix

The first live execution reached `openai/gpt-5.4-mini` and persisted seven completed usage events, but it also exposed two different failure classes:

- the `ExternalLLMChatEngine` adapter omitted safe provider/model/usage metadata, producing false provider-health and observability failures even though `AIUsageEvent` existed;
- the model sometimes confirmed facts, intent changes or object reads in prose without requesting the typed tools that update/read My Scoope state.

The calibration hotfix keeps the conversation adaptive while strengthening the product boundary:

```text
plain text does not mutate state
state/read/card claims require matching tools
AIUsageEvent is authoritative provider evidence
```

It also requires explicit share tools in card-review scenarios and detects responses that claim tools are unavailable after a real tool result exists. A second live run is required; the first report does not close CM24.

Decision: `docs/20_decisions/0110-ai-assistant-tool-grounded-state-claims.md`.

#### Second live run and strict provider transport hotfix

The second live run confirmed that the provider and `AIUsageEvent` bridge were healthy. It also reproduced malformed/truncated envelopes (`{`), contract-error fallbacks and text-only operational responses. These failures are classified as provider transport/tool-grounding defects, not reasons to restore deterministic intake order.

The strict transport hotfix adopts `ai_assistant_structured_response.v2` through provider-enforced JSON Schema, adds an explicit `tool_plan`, and allows one bounded repair call for malformed, incomplete or operationally ungrounded envelopes. Safe parse/repair/incomplete diagnostics are forwarded into the CM24 report. The normal 900-token product cap is preserved; only the controlled live harness raises its bounded budget to 1,400 with low reasoning effort.

This intermediate design required a third live run. That run was executed and demonstrated that nested textual tool payloads remained unreliable; the transport is superseded by the native function-call boundary documented below.

Historical decision: `docs/20_decisions/0111-ai-assistant-strict-structured-provider-transport.md`.

#### Third live run and native function-call transport hotfix

The third live run confirmed that the strict visible-text schema works for a greeting, but operational turns still truncated or failed while serializing tool calls inside nested JSON. The model often produced an appropriate pre-tool acknowledgement, yet the action payload itself did not survive the textual envelope.

CM24 therefore moves OpenAI operations to the Responses API native function channel:

```text
provider function_call
-> My Scoope validation and execution
-> function_call_output
-> final structured visible response
```

The visible JSON schema no longer contains `tool_plan`, tool names or JSON-string arguments. Stateless continuation keeps bounded provider output items and encrypted reasoning content while `store=false` remains active. Function declarations, continuation items and outputs are included in local input-limit estimation, and custom-function counts remain enforced by My Scoope.

A fourth complete live run plus human transcript disposition was required before CM24 could close.

Decision: `docs/20_decisions/0112-ai-assistant-native-provider-function-call-transport.md`.

#### Fourth live run and post-tool resilience hotfix

The fourth live run validated the native function channel in the principal operational paths: the grouped-data scenario executed five native calls, and the direction-change scenario executed three with all hard checks passing. It reduced the remaining failures to two narrow contracts rather than another transport redesign.

`complexity_level` existed in `NutritionBrief` readiness but was absent from `update_proposal_preferences`, so “algo simple” could not be committed to the proposal draft. CM24 now treats proposal complexity as a typed proposal preference with canonical values `low|medium|high`.

The missing-proposal scenario also proved that a native `read_proposal` call and its typed `not_found` result could succeed before the provider failed on the follow-up wording request. The runtime now preserves that evidence and returns a minimal local acknowledgement derived strictly from the tool result. It does not invoke deterministic intake or invent a next step.

A fifth full live run plus human transcript disposition is required before CM24 and this alignment extension can close.

Decision: `docs/20_decisions/0113-ai-assistant-proposal-complexity-and-post-tool-resilience.md`.

#### Fifth live run and explicit proposal-preference schema

The fifth live run passed the greeting, direction-change and missing-proposal scenarios. It also confirmed five native calls in the grouped-data scenario, correct cards, complete provider/usage observability and successful post-tool recovery. Only `complexity_level` remained empty.

The model understood “algo simple” and reflected it in visible copy, but the native `update_proposal_preferences` declaration exposed `updates` as a generic object whose supported fields existed only in a prose description. Goal, entity and meals were sent; complexity was omitted.

CM24 now exposes proposal preference fields as compact, machine-readable nested properties. `complexity_level` has the canonical enum `low|medium|high`, and the grouped operational example explicitly keeps `meals_per_day=4` and `complexity_level=low` in the same call. My Scoope still performs final normalization and does not parse the assistant's prose to recover missing state.

A sixth full live run plus human transcript disposition is required before CM24 and this alignment extension can close.

Decision: `docs/20_decisions/0114-ai-assistant-explicit-proposal-preference-function-schema.md`.

#### Sixth live run and capability-scoped strict arguments

The sixth live run confirmed that native function calling and the operational runtime were stable: greeting, direction changes and missing-proposal recovery passed; the grouped turn executed `read_user_profile_context`, `update_profile_draft` and `update_proposal_preferences`. The remaining failures had two concrete causes.

First, the provider-facing proposal schema exposed `complexity_level` but still used best-effort optional arguments, so the model could acknowledge “algo simple” in visible text while omitting the field from the function call. `update_proposal_preferences` now uses a strict nullable provider schema: every supported update field is explicit, absent values are `null`, and My Scoope removes nulls before local validation.

Second, CM24 disabled reviewable proposal execution but the provider still received all proposal-tool schemas. The second turn exceeded the local input guardrail before reaching OpenAI. The provider catalog now mirrors the runtime capability flag and omits proposal-category tools when they cannot be executed. This reduces context without increasing product limits or choosing the conversation path deterministically.

A seventh full live run plus human transcript disposition is required before CM24 and this alignment extension can close.

Decision: `docs/20_decisions/0115-ai-assistant-capability-scoped-tools-and-strict-nullable-proposal-arguments.md`.

#### Seventh live run and proposal-complexity state-sync hotfix

The seventh live run passed provider health, native function transport, tool contracts, card pacing, usage observability, direction changes and missing-proposal recovery. The grouped-data scenario executed all five expected tools, and its proposal card visibly contained low complexity. Only the final brief projection remained wrong: `complexity_level` was `None`, so readiness stayed false.

This was not another provider omission. `_apply_proposal_preferences_to_brief()` maintained an explicit field allowlist that omitted `complexity_level`. Because the proposal draft already contained the field, the redundant `nutrition_brief_patch` intentionally removed it before applying provenance-safe fallback updates. The value therefore disappeared only at the local draft-to-brief projection boundary.

CM24 now copies `complexity_level` and its canonical source alongside the other proposal-scoped fields. No prompt, tool schema, parser, input limit or conversational rule changes.

An eighth full live run plus explicit human transcript disposition is required before CM24 and this alignment extension can close.

Decision: `docs/20_decisions/0116-ai-assistant-proposal-complexity-state-sync-completeness.md`.

#### Eighth live run and state-only post-tool UX correction

The eighth full live report passed every automated CM24 invariant: provider health, native function transport, grouped state capture, proposal readiness, card pacing, intent transitions, typed tool recovery and usage observability.

Human transcript review identified one remaining UX defect in `cambio_de_direccion`. All three proposal updates succeeded, but each post-tool provider wording call failed. The local technical acknowledgement then repeated the same profile-source question, including after the user said to advance without more preferences.

The defect was local, not provider-semantic: `_local_acknowledgement_from_tool_results()` appended a backend-selected next step whenever a proposal had a goal but no profile draft. That recreated a deterministic interviewer inside the transport fallback.

CM24 now treats post-tool local acknowledgements as state-only. They summarize validated results but do not choose a question or missing-field agenda. Proposal changes produce concise controlled copy such as:

```text
Perfecto. La propuesta queda como un programa semanal para bajar grasa, con 3 comidas al día.
```

The CM24 report exposes the local-ack policy and adds the hard invariant `post_tool_fallback_pacing`. A targeted live rerun of `cambio_de_direccion` plus human disposition is the remaining closure evidence.

Decision: `docs/20_decisions/0117-ai-assistant-post-tool-local-ack-state-only.md`.
