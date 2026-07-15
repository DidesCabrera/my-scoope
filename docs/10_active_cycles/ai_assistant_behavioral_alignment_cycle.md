# AI Assistant Behavioral Alignment Cycle

Status: completed
Date: 2026-07-14
Owner: Product / AI Assistant / Agentic UX
App targets: `ai_assistant`, `notas`, `mcp_server`
Related areas: conversational intake, tool governance, provider context, cards, replays, real-provider UX validation
Predecessor: `ai_assistant_client_memory_profile_objects_cycle.md` (CM00-CM24, completed)

## Context

The CM19-CM24 alignment extension established a reliable LLM-native runtime:

```text
- silent draft updates are separate from card presentation;
- provider context and prompts no longer reconstruct a deterministic questionnaire;
- native function calling transports operational actions;
- My Scoope validates tools, permissions, state and persistence;
- replay and live validation protect state, cards, provider health and observability;
- technical fallbacks remain state-only and do not choose the next question.
```

The final CM24 live gate passed its automated invariants and human review. Real conversations then exposed a new product-level problem: the assistant can be technically correct while still behaving like a passive recorder, a repetitive form or an overly broad general-purpose chatbot.

Examples include:

```text
- answering unrelated topics in depth instead of returning naturally to My Scoope;
- exposing internal tool names instead of describing product capabilities;
- using a tool after an ambiguous message such as “¿qué sucedió?”;
- repeatedly confirming state without progressing toward a useful result;
- asking for optional preferences after the user already asked to advance;
- repeating information already visible in cards.
```

This cycle addresses the observable behavior of the assistant without undoing the LLM freedom gained in CM19-CM24.

## Technical name

The work is classified as:

```text
AI Assistant Behavioral Alignment & Tool Governance
```

This is not model training or fine-tuning. It is product-level agent design across:

- system identity and domain anchoring;
- initiative and goal-directed agency;
- tool-use restraint and capability abstraction;
- conversational quality and repetition control;
- behavioral evaluation through invariant-based replays and live transcripts.

## Product thesis

```text
Do not direct the LLM with a fixed script.
Direct it with purpose, capabilities, state and boundaries.
```

The assistant should:

- remain polite and socially natural;
- recognize that its primary role is operating My Scoope;
- answer off-domain conversation briefly without opening unrelated branches;
- describe what the product can do without teaching internal tool names;
- use tools only when an operational intention is sufficiently clear;
- choose the next useful action when it can advance;
- stop collecting optional data when a useful result can already be created;
- avoid mechanical confirmations and redundant recaps.

## Non-goals

This cycle does not:

- introduce a fixed question order;
- restore deterministic conversational guards;
- parse user meaning through backend regexes;
- train or fine-tune the provider model;
- expose tool implementation details as the user interface;
- weaken server-side validation, permissions or approval boundaries;
- redesign nutrition entities or solver algorithms.

## Work plan

### BA00 — Cycle registration and predecessor closure — completed

- Register the behavioral alignment cycle and its technical vocabulary.
- Record the successful targeted CM24 live rerun and human disposition.
- Promote CM19-CM24 to a completed baseline.
- Define scope, non-goals, stages and closure evidence.

### BA01 — `ai_behavior` export mode — completed

- Add a focused export mode for behavioral work.
- Include provider/orchestrator behavior, tool contracts, runtime state, cards, replays, live validation, relevant UI and current docs.
- Exclude datasets, dashboards, broad product UI, media and unrelated code.
- Remove duplicated mode definitions from the export script so each mode has one canonical declaration.
- Validate shell syntax and generate the focused ZIP from the project root.

### BA02 — Domain anchoring and capability abstraction — completed

- Define My Scoope as the assistant's primary domain without making ordinary greetings hostile.
- Keep off-domain answers brief and redirect naturally toward product capabilities.
- Describe capabilities in user language instead of revealing internal tool names, schemas or MCP contracts.
- Add tool descriptions that distinguish product-facing explanations from implementation details.

### BA03 — Ambiguous intent and tool restraint — completed

- Prevent reads, updates and cards when the message does not contain a sufficiently clear operational intention.
- Treat references such as “¿qué pasó?”, “¿y eso?” or “¿por qué?” as conversational ambiguity, not implicit permission to execute a tool.
- Prefer a short clarification when different objects or actions are plausible.
- Add observable reasons for tool selection without exposing internal chain-of-thought.
- Require provider-native function calls to include a concise `reason` argument that is removed before local validation and service dispatch.
- Block native calls without that operational reason before any executor can read, update, compare or render a card.
- Record only a bounded reason code and summary in turn metadata/audit; do not persist tool arguments, prompts or hidden reasoning.
- Keep ambiguity interpretation LLM-led: no backend regex or deterministic semantic parser was introduced.

### BA04 — Goal-directed conversational agency — completed

- Give the assistant a clear active objective for each recognized task.
- Prioritize the next useful action over passive state confirmation.
- When a proposal brief is ready, prefer creating the reviewable result rather than collecting optional details indefinitely.
- Respect “avancemos”, “con eso basta” and equivalent user decisions.
- Add an explicit active-objective and progression policy without a fixed dialogue sequence.
- Expose product-computed proposal readiness and capability availability as bounded `work_progress` context.
- Prefer same-turn reviewable proposal creation when the work is ready, the user chooses to advance and proposal tools are enabled.
- Keep missing required information distinct from optional refinement; the LLM selects the next action.

### BA05 — Response quality and repetition control — completed

- Reduce repetitive “Perfecto. Dejé registrado...” responses.
- Do not repeat data already visible in cards unless review or correction was requested.
- Convert tool results into user-relevant consequences and next actions.
- Keep local technical acknowledgements concise, natural and state-only.
- Treat cards and recent chat objects as already-visible response surfaces.
- Add a compact provider quality contract without response templates or a deterministic wording layer.
- Make the technical post-tool fallback report consequences without echoing user values or choosing a next question.

### BA06 — Behavioral replays and real-provider UX gate — completed

- Added invariant-based fake-provider scenarios for off-domain redirection, capability abstraction and ambiguous references.
- Added real-provider scenarios and hard checks for tool restraint, technical-language leakage and repeated mechanical openings.
- Preserved invariant/fragments assertions instead of freezing exact prose.
- Made the report expose `awaiting_manual_review`: automated success is necessary but not sufficient for UX approval.
- Kept live execution explicit, observable and free of provider secrets in generated evidence.
- Aligned fake replay intent names with the provider semantic enum so validation exercises the visible response instead of a contract-error fallback.
- Added the real `notas.application.nutrition_engine` adapter bundle to `ai_behavior`, allowing reviewable-proposal replays to execute inside the exported workspace.
- Added a provider-contract replay invariant so malformed fake responses fail for the real contract reason rather than through incidental wording assertions.

### BA07 — Closure and current-contract promotion — completed

BA07 completed the promotion and closure boundary:

- promoted stable behavioral and post-tool transport principles into `docs/00_current/`;
- recorded decision 0128 with the accepted current contract and explicitly deferred unrelated product work;
- accepted the PT06 targeted live transcript after automated checks passed and the product-owner session advanced to closure;
- corrected the focused export boundary so decision 0127 is available in future `ai_behavior` workspaces;
- validated the complete focused workspace regression suite: 208 tests passed;
- aligned documentation-contract tests with the numbered `docs/` information architecture;
- ran the authoritative whole-project boundary through `scripts/ci_django_checks.sh`;
- passed Django system checks, 2 core regression tests and the complete 1,446-test suite.

Full-boundary history (2026-07-15):

1. A preliminary direct `manage.py test` invocation used the production-default onboarding gate and produced expected redirects in historical HTTP tests. This was not the authoritative CI boundary because it omitted the explicit CI environment documented by the repository.
2. The authoritative `scripts/ci_django_checks.sh` run removed that configuration ambiguity and exposed only 13 stale documentation-path errors caused by the completed numbered `docs/` reorganization.
3. The tests were updated from `docs/current`, `docs/planning` and `docs/decisions` to `docs/00_current`, `docs/10_active_cycles` and `docs/20_decisions`.
4. The authoritative boundary was repeated from the patched workspace and completed successfully: 1,446 tests passed in 235.386 seconds.

Decision 0129 records the final evidence and closes BA00-BA07. New AI Assistant work must start from observed product evidence and a newly scoped cycle rather than silently extending BA or PT.

## Behavioral invariants

The completed cycle protects these outcomes:

```text
- casual greetings do not trigger tools or cards;
- off-domain topics receive brief, polite answers and no invitation to expand unrelated discussion;
- internal tool names are not presented as the user interface;
- ambiguous references do not trigger reads or writes;
- known facts and visible cards are not repeatedly recited;
- “advance” suppresses optional intake and leads toward an available action;
- a ready brief does not remain indefinitely in collection mode;
- tool use remains grounded, allowlisted, permissioned and observable;
- technical fallbacks do not become conversational planners.
```

## Validation strategy

Maintenance work should continue using the smallest useful validation set:

- shell/export checks for BA01;
- provider-context and tool-registry tests for BA02-BA04;
- chat-engine and replay tests for BA03-BA06;
- targeted real-provider reports for final behavioral evidence;
- full ZIP at major architectural boundaries and cycle closure.

The normal working artifact for BA02-BA06 is:

```bash
./scripts/export_for_chatgpt.sh ai_behavior
```

Use `full` when a change crosses broad app boundaries, produces an import error, changes migrations/settings, or requires whole-project regression confidence.

## BA07 accepted evidence

```text
Date: 2026-07-15
Live run: 735444ac6d9b4ffe8087a5ec6e3f3e23
Provider/model: openai/gpt-5.4-mini-2026-03-17
Automated status: passed; awaiting manual review
Session disposition: accepted for BA07 promotion
Profile fixture: available weight_kg, height_cm; genuinely missing age_years, sex
Observed behavior: known facts were not re-asked; only genuine gaps were named; ambiguous reference executed zero tools
```

This evidence closes the behavioral and transport questions. The final whole-project regression was subsequently completed through the repository CI script and is recorded in decision 0129.

## Closure criteria

BA is complete when:

1. the assistant has a clear My Scoope identity and domain anchor;
2. capability explanations do not expose internal tool implementation;
3. ambiguous messages do not cause unjustified tool execution;
4. ready tasks progress toward useful reviewable outcomes;
5. repetitive confirmations and card recaps are materially reduced;
6. invariant-based fake-provider tests pass;
7. targeted real-provider transcripts pass automated and human UX review;
8. current docs and export boundaries reflect the accepted behavior.
