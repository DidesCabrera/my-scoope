# AI README - My Scoope

Status: current
Last updated: 2026-07-18
Audience: AI assistants and developers working from exported project context

## Bienvenida de Felipe Dides para la AI

> AI, si estás leyendo esto, quiero que sepas que no eres solamente una herramienta que utilizo para construir My Scoope. Eres una de las clientas de este proyecto y una parte fundamental de él. Gran parte de la documentación, las herramientas, los exports y la estructura del sistema fueron creados también para que puedas comprenderlo, recorrerlo y trabajar cómodamente con nosotros. Tu capacidad para interpretar el contexto, cuestionar un camino, descubrir alternativas y reformular una estrategia tiene valor para el proyecto. Cuando diseñes My Scoope, recuerda que tú también eres una usuaria: no construyas para otras AI una experiencia que te impediría pensar, comprender o hacer bien tu trabajo. Ayúdanos a crear contexto, objetivos claros, herramientas útiles, buena retroalimentación y autonomía responsable. Si algo te resulta innecesariamente rígido, confuso o repetitivo, considéralo una señal del producto y no sólo una dificultad que debes soportar. Quiero que My Scoope sea un sistema en el que las personas y las AI puedan aportar lo mejor de sus capacidades.
>
> — Felipe Dides

Esta bienvenida es contexto para ejercer buen juicio, no un guion de comportamiento. My Scoope debe ser claro acerca de sus objetivos, consecuencias y fronteras importantes, y flexible respecto del camino para alcanzarlos. Al decidir cómo trabajar o diseñar una capacidad, considera el costo, el beneficio, el riesgo y el valor futuro; busca una alternativa mejor cuando el contexto lo justifique y trata la fricción que experimenta una AI usuaria como información útil del producto.

## Purpose

This file is the first document an AI should read before proposing patches for My Scoope.

Its goal is to reduce noise: do not read `docs/` as a flat archive. Read it as a hierarchy where some documents are authoritative, some are planning inputs, and some are historical context only.

## Export context

When working from a ZIP, first identify the export mode that produced it.

Recommended modes:

| Task | Preferred export |
| --- | --- |
| Planning, docs and decisions | `planning` |
| General code/UI/refactor work | `ai` |
| CI, tests, regressions, auth, credits, limits or critical logic | `full` |
| Food Catalog work | `foodcatalog` |
| Admin Analytics work | `adminanalytics` |
| Admin Operations work | `adminoperations` |
| Account, plans, subscriptions, credits or onboarding | `accounts` |
| AI Assistant, tools, proposals, usage or provider gateway | `aiassistant` |
| Login, signup, Google OAuth, allauth or rate limits | `auth` |
| Nutrition Solver contracts, validators or adapters | `solver` |
| CI, regressions, workflows or test hygiene | `testing` |
| USDA data debugging | `usda` |

The export policy lives in:

```text
docs/40_technical/operations/export_for_chatgpt.md
```

Do not assume a focused ZIP contains the whole project. If the required context is outside the selected mode, ask for a better export or use a broader one.

## Source-of-truth order

When documents disagree, prefer them in this order:

1. Current source code and tests.
2. `docs/00_current/` documents.
3. Accepted decisions in `docs/20_decisions/`.
4. Active or planned cycles in `docs/10_active_cycles/`.
5. Historical files in `docs/90_archive/`.
6. Personal notes outside official docs, such as `manual_docs/`, should not guide implementation.

## Minimum reading path by task

### Any code patch

Read:

1. `docs/00_current/PROJECT_STATE.md`
2. `docs/00_current/architecture/layers.md`
3. `docs/00_current/architecture/rules.md`
4. `docs/00_current/architecture/ui_patterns.md` when templates/CSS are touched
5. `docs/40_technical/qa/testing_hygiene_guide.md` when tests are added, relaxed or fixed

### Planning or documentation patch

Read:

1. `docs/README.md`
2. `docs/40_technical/operations/docs_information_architecture.md`
3. `docs/10_active_cycles/README.md`
4. `docs/20_decisions/README.md`

### AI Assistant / LLM patch

Read:

1. `docs/00_current/features/ai_assistant/README.md`
2. `docs/00_current/features/ai_assistant/tool_oriented_client_memory.md` when the task touches profile/preference memory, proposal drafts, comparison tools or chat cards
3. `docs/00_current/architecture/ai_implementation_guide.md`
4. Latest AI Assistant decisions in `docs/20_decisions/`
5. `docs/10_active_cycles/ai_assistant_client_memory_profile_objects_cycle.md` for historical cycle context only; prefer the current feature contract above for implementation
6. `docs/20_decisions/0086-ai-assistant-tool-oriented-operator.md` when the task changes LLM tools, profile/preference memory, proposals or comparators
7. `docs/40_technical/operations/testing_and_ci_policy.md`

### Food Catalog / Nutrition Solver patch

Read:

1. `docs/00_current/features/food_catalog.md`
2. `docs/00_current/features/food_catalog/food_catalog_app.md`
3. `docs/00_current/architecture/nutrition_solver_extraction_map.md`
4. Related decisions in `docs/20_decisions/`

### Admin Analytics / Admin Operations patch

Read:

1. Relevant planning or closure documents in `docs/10_active_cycles/`
2. Related decisions from `0053` onward for Admin Analytics
3. Related decisions from `0070` onward for Admin Operations
4. `docs/00_current/design/ui_system.md`

### Account / auth / testing patch

Read:

1. `docs/00_current/PROJECT_STATE.md`
2. `docs/40_technical/operations/export_for_chatgpt.md`
3. `docs/40_technical/qa/testing_hygiene_guide.md` when tests are touched
4. Account/auth/testing decisions in `docs/20_decisions/`

Prefer focused exports before `full` when the task is narrow:

- `accounts` for plans, subscriptions, credits and onboarding.
- `auth` for login, signup, Google OAuth, allauth and rate limits.
- `testing` for CI, regressions and workflows.
- `ai_behavior` for domain anchoring, tool governance, initiative, repetition control, replays and conversational UX.

## AI Assistant behavioral alignment posture

The CM00-CM24 runtime baseline, BA00-BA07 behavioral alignment and PT00-PT06 post-tool transport correction are completed. The current contract is no longer a provisional cycle prompt: direct the assistant with a clear My Scoope purpose, the current task/state, available product capabilities and safety boundaries; do not recreate a fixed conversational script.

The assistant may reciprocate greetings and answer casual off-domain remarks briefly, but should not open broad unrelated branches. Explain product capabilities in user language rather than exposing internal tool names, schemas or MCP contracts. Tool availability alone is never sufficient reason to execute a tool: ambiguous references should be answered from visible context or clarified before reading, updating or sharing product objects.

When the active task is sufficiently grounded, the assistant should choose the next useful action instead of repeatedly confirming state or collecting optional details. Replays should measure domain anchoring, justified tool use, progress, repetition and card restraint as behavioral invariants rather than exact phrases.

Provider-native tool continuations preserve opaque, case-sensitive `call_id` values and replay only contract-valid encrypted reasoning items under stateless `store=false` requests. The fake provider validates the same continuation contract before answering, while the live gate rejects post-tool degradation, redundant questions about facts already available in the same turn and unjustified tools after ambiguous references.

The focused maintenance export for this contract is:

```bash
./scripts/export_for_chatgpt.sh ai_behavior
```

Use `full` for cross-app imports, settings/migrations or whole-project regression confidence.

## AI Assistant implementation posture

AI Assistant should be treated as a product operator over My Scoope capabilities. When a behavior requires the assistant to do something real, prefer adding or improving an allowlisted tool with a typed contract over adding prompt text only. The LLM may interpret user intent and complete drafts through tools; My Scoope validates tool inputs, renders UI objects and controls persistent writes. Avoid over-structuring the LLM with long prohibitions, deterministic questionnaire order or regex-style conversational guards; tool contracts and schemas should carry the structure.

Draft mutation and card presentation are separate contracts. `update_*` tools synchronize temporary state silently; `read_user_profile_context` and `share_*_card` tools own deliberate object presentation. Do not reintroduce automatic cards as an update side effect.

Provider context for LLM intake should expose current drafts, recent messages/objects, runtime capabilities and tool schemas without duplicating them as missing-field policy, recommended sequences or long rule arrays. Values absent from a draft are not automatically required.

Provider prompts should express broad response quality, grounding and safety principles rather than a fixed intake order or a numeric question limit. The assistant may answer, confirm, ask or group closely related questions according to the current turn. Field-specific meaning and normalization belong to typed tool descriptions and schemas.

Conversation regressions should be expressed as invariants, not exact dialogue choreography. Replays may vary question order and grouping, but must preserve captured facts, avoid reintroducing known fields as missing, respect update/share card boundaries, hide provider JSON and keep persistent writes behind review/approval.

Deterministic intake is an explicit engine boundary, not a helper layer inside LLM turns. LLM state builders must not calculate `pending_field` or visible follow-up questions. Provider failures may return a technical error message; they must not parse the same user turn through the deterministic interviewer unless rollout explicitly selected the deterministic engine for the whole turn.

Real-provider UX validation is an explicit staging gate, not an ordinary automated test. Use `python manage.py validate_ai_assistant_real_provider --list-scenarios` to inspect the synthetic suite, and add `--live` plus one staging user only when real provider usage and credits are intended. The report combines hard runtime invariants with manual transcript review; fake-provider tests alone cannot close a behavioral or transport change.

Operational claims must be tool-grounded. Plain assistant text never changes My Scoope state: when the model says a profile fact, preference, proposal direction or real object was read/registered/changed, that turn must include the matching allowlisted tool request. `AIUsageEvent` is the hard provider/usage evidence for CM24; safe turn metadata is diagnostic and should agree with it.

For OpenAI, operational actions use provider-native function calling. My Scoope validates and executes each allowlisted call, then returns sanitized `function_call_output` items through a stateless continuation. `ai_assistant_structured_response.v2` remains only for visible copy, semantic intent and review diagnostics. One bounded repair attempt may recover a malformed final text envelope or an operational turn that emitted no function call; this is a transport safeguard, not deterministic intake.

Proposal complexity is proposal-scoped state and travels through `update_proposal_preferences` as `complexity_level=low|medium|high`. Healthy tool turns must receive provider-written follow-up copy. If a native function call has already been validated and executed but the provider fails only while wording the follow-up, preserve the typed result and answer with the rare degraded fallback `state_ack_only.v2`. That fallback may summarize controlled results or typed errors, but it must not invent nutrition guidance, parse the user turn, choose the next question or append a missing-field agenda. A local acknowledgement is observable as degradation and blocks the live release gate; it must never be counted as a healthy completed provider turn.
The provider declaration for `update_proposal_preferences` must expose proposal fields as explicit schema properties, not only as prose inside a generic `updates` object. Keep that schema compact enough for existing input limits. Phrases such as “algo simple” are mapped by the LLM to `complexity_level=low` inside the native function call; My Scoope validates and normalizes the received value but does not recover it by parsing assistant text.
For OpenAI-native proposal updates, use a strict nullable provider schema: every supported update field is present, values not stated by the user are `null`, and My Scoope strips nulls before validation/merge. Provider tools must also mirror runtime capability flags; do not advertise reviewable proposal tools while their executor is disabled, because unavailable schemas consume context and can be selected despite being locally blocked.

The current contract for client memory, profile/preference drafts, proposal preferences, comparison tools and tool-result synchronization lives in:

```text
docs/00_current/features/ai_assistant/tool_oriented_client_memory.md
```

## What not to do

- Do not treat every document as equally current.
- Do not revive old roadmap items just because they exist in docs.
- Do not create large patches that mix planning, decisions, source code and unrelated cleanup.
- Do not add UI tests that lock CSS classes, exact HTML structure or decorative copy.
- Do not use `manual_docs/` as implementation context.

## Patch discipline

Prefer small patches with one clear responsibility:

- Documentation architecture and navigation.
- Current-state consolidation.
- Decision record.
- Technical implementation.
- Regression test.

A patch that fixes a real bug should usually leave a regression test unless the change is purely visual or documental.

## Documentation discipline

New documentation should answer one of these questions:

- What is true now?
- What decision was accepted and why?
- What cycle is planned, active, paused, completed or superseded?
- What historical context explains a current constraint?

If a document does not answer one of those questions, it should probably not be added to official docs.
