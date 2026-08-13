# Consumer Mobile Enrichment — One-Day Cycle

Status: completed in repository — physical iPhone smoke remains external
Date: 2026-08-13
Cycle code: MCE00-MCE08
Execution window: one focused working day
Last reviewed: 2026-08-13 — MCE00-MCE08 completed with all repository gates green.

## Objective

Enrich the React Native consumer app in one integrated repository cycle so an
authenticated user can manage the lived program, compare nutrition entities,
review and apply AI proposals, and converse with the AI Assistant without
returning to the Django web interface.

The completed journey is:

```text
AI Assistant
  -> reviewable NutritionProposal
  -> explicit approval and application
  -> resulting library entity
  -> Program
  -> ProgramCalendarization
  -> Today execution
```

The cycle is deliberately vertical. Each patch must include the necessary mobile
API contract, React Native surface, permission boundary and focused tests. It must
not create UI-only placeholders that depend on a future backend patch.

## One-day execution rule

The one-day constraint changes sequencing, not product safety:

- reuse existing selectors, application services and commands;
- keep Django authoritative for nutrition, ownership, proposal lifecycle,
  comparisons and calendarization;
- expose narrow screen-oriented mobile contracts instead of porting Django views;
- use the existing React Native primitives, entity cards and navigation shell;
- prefer one coherent first version of every feature over optional polish;
- preserve all current uncommitted work and never reset or overwrite unrelated
  changes;
- keep AI and OCR writes behind explicit user review;
- do not weaken ownership, idempotency, validation or audit requirements to meet
  the timebox.

Repository completion is the target for the day. Signing, App Store review,
production rollout and physical-device credentials remain external gates.

## Product and architecture invariants

- `Program` is an editable template; `ProgramCalendarization` is the lived
  dated program.
- Today continues to resolve from the single current calendarization.
- Calendarized snapshots and past execution evidence are never silently rewritten.
- A `NutritionProposal` is reviewed before approval and explicitly applied before
  it creates or changes a final entity.
- The AI provider cannot invoke final proposal application or prepared-action
  commit tools directly.
- Comparator calculations and saved snapshots come from existing comparison
  services; React Native does not reproduce nutrition math.
- Foods use quantities in comparisons; Meals and DailyPlans do not. Programs
  remain outside comparator scope.
- AI turns use the durable async queue and idempotency contract already exposed by
  the mobile API.
- Chat renders typed product objects. Provider prose is never interpreted by the
  client as permission to mutate product state.
- The API retains the `{ok, data, error}` envelope, mobile scopes and owner-scoped
  resource resolution.

## Scope

### In scope

- mobile navigation for Home, My Program, Assistant, Proposals, Comparator,
  Libraries and Account;
- calendarization activation and lifecycle management;
- active-program calendar and calendarized-day detail;
- NutritionProposal list, detail, approval, rejection and application;
- dynamic comparisons for Foods, Meals and DailyPlans;
- saved comparison list/detail and save/update path if the existing command can be
  projected without introducing a parallel mutation model;
- AI chat history, new/resumed conversations and durable async turns;
- typed chat rendering for supported draft, proposal, comparison and prepared
  action cards;
- cross-navigation between chat, proposals, comparisons, libraries,
  calendarization and Today;
- focused backend/mobile contract tests and one end-to-end repository smoke.

### Deferred from the one-day repository cycle

- Programs comparator;
- nutritionist, invited-client or seat-purchase flows;
- general library composition/editing beyond actions required by this journey;
- arbitrary client-authored calendarization revisions;
- a generic offline mutation queue;
- Android-specific behavior;
- chat streaming transport;
- new database models when an existing aggregate already owns the behavior;
- visual redesign of the existing mobile grammar;
- App Store, production rollout and external credentials.

## Execution order

```text
MCE00 baseline and contract map
  -> MCE01 shared mobile contracts and navigation
  -> MCE02 My Program/calendarization
  -> MCE03 Proposals
  -> MCE04 Comparator
  -> MCE05 AI chat transport and history
  -> MCE06 typed chat objects and trusted actions
  -> MCE07 integrated journey and hardening
  -> MCE08 evidence and closure
```

Calendarization lands first because it completes the product's principal daily
loop. Proposals land before chat because proposal cards require a trusted mobile
review and application destination. Comparator lands before typed chat objects so
comparison results can link to a real mobile surface. Chat transport then composes
those already available capabilities.

## Patches

### MCE00 — Baseline, scope freeze and dependency map

Status: completed.

Goal: establish a safe starting point without disturbing current work.

- Inspect and preserve the dirty worktree; record files already changed by the
  library/navigation and nutrition-panel work.
- Confirm current API paths, OpenAPI generation, React Native routes and reusable
  UI primitives.
- Freeze the screen/endpoint matrix in this document before implementation grows.
- Identify existing application services for every mutation; no mobile endpoint
  may write domain state directly when a command already exists.
- Run fast structural/mobile baselines, recording pre-existing failures separately.

Exit evidence:

- no user change was overwritten;
- every planned endpoint has an owning selector/query or command;
- the baseline failure list is known before feature work begins.

### MCE01 — Shared mobile contracts and navigation

Status: completed.

Goal: create the common skeleton used by all four capabilities.

- Add navigation entries for `Mi programa`, `Asistente`, `Propuestas` and
  `Comparador` while preserving the four entity libraries.
- Add mobile API types for pagination, action capabilities, proposal summaries,
  comparison results, calendarized days, chat summaries/messages/cards and async
  job state.
- Add reusable screen states for initial loading, refresh, empty result, recoverable
  error and destructive/important confirmation.
- Define stable internal links from typed cards to their trusted destinations.
- Add a bounded async polling helper with cancellation on unmount, retry timing from
  the server and no duplicate turn submission.

Exit evidence:

- all new routes resolve;
- TypeScript compiles before feature screens are filled;
- navigation tests enumerate the new product areas;
- no raw internal JSON type is treated as an unbounded client contract.

Delivered result:

- A central product-area catalog now records Home, My Program, Assistant,
  Proposals and Comparator with explicit `available` or `planned` state.
- The sidebar derives visible product destinations from that catalog. Planned
  destinations remain hidden until their backing route/API is functional, so this
  patch introduces no dead link or placeholder screen.
- Shared TypeScript contracts cover active-program days, proposal summaries and
  details, supported comparison requests/results, durable AI jobs, chat history and
  a discriminated union of typed chat cards.
- Shared empty, recoverable-error and confirmation states are ready for the vertical
  feature screens.
- The durable polling helper follows server retry timing, bounds total polling,
  cancels cleanly and fails closed when a successful job omits its typed result.
- Four polling tests and two navigation-catalog tests extend the mobile suite.

### MCE02 — My Program and calendarization

Status: completed.

Goal: remove the current requirement to calendarize a Program from the web.

Backend/API:

- expose owned Programs eligible for activation using the existing library/read
  boundary;
- expose current calendarization with its complete dated-day summary;
- expose calendarized-day detail and bounded history;
- add activation, pause, resume and cancel endpoints over the existing commands;
- preserve explicit confirmation for incomplete Programs and replacement of the
  current calendarization;
- reuse the current reminders endpoint and notification delivery-mode contract.

React Native:

- add `Mi programa` with active status, date range, progress and dated days;
- open past, current and future day detail from the program calendar;
- add activation from `Mi programa` and from a Program library detail;
- collect start date, timezone, daily notification time and notification toggles;
- show explicit incomplete/replacement confirmations returned by stable error codes;
- add pause, resume, cancel and history actions;
- replace the Today message that sends the user to the web with a native activation
  action.

Exit evidence:

- a user with an owned Program can activate it entirely from the mobile app;
- activation immediately changes Today through the canonical `/today` read;
- lifecycle actions do not change the source Program or historical snapshots;
- past/current execution safety remains covered by existing calendarization tests.

Delivered result:

- The consumer API now exposes activation, bounded history, owner-scoped day
  detail, and pause/resume/cancel operations over the existing calendarization
  commands. No new aggregate or parallel mutation path was introduced.
- Incomplete Programs and replacement of the current calendarization remain
  explicit confirmations with stable error codes and structured details.
- `Mi programa` is a functional product destination with current status, progress,
  dated days, lifecycle actions and historical calendarizations.
- Activation is available from `Mi programa`, Today and Program library detail;
  it collects start date, timezone, daily time and reminder preferences.
- Calendarized-day detail renders the immutable plan snapshot and preserves a
  clear empty-day state when no plan was assigned.
- The committed OpenAPI contract includes all six new calendarization paths.
- Validation passed with Django system check, 21 mobile API tests, strict
  TypeScript, Expo lint, 18 mobile tests and a 27-route Expo web export.

### MCE03 — Mobile proposal center

Status: completed.

Goal: provide the trusted review surface required by AI-generated outcomes.

Backend/API:

- add owner-scoped proposal list and detail endpoints using
  `proposal_queries` DTOs;
- create an explicit mobile projection of proposal content, validation, before/after
  facts, warnings, status and allowed actions;
- add approve, reject, cancel and apply endpoints over proposal commands;
- translate command failures to stable API error codes;
- keep approval and application distinct and idempotent;
- return the resulting entity identity/link after successful application.

React Native:

- add proposal filters for pending, applied and rejected outcomes;
- show a pending count in the navigation or Home entry point;
- add proposal detail with summary, targets, proposed entity, validation and audit
  status relevant to the user;
- show explicit confirmation before approve/reject/apply;
- preserve the external/manual subject warning and acknowledgement requirement;
- navigate to the created Meal or DailyPlan after application.

Exit evidence:

- a proposal generated by AI can be reviewed, approved and applied on mobile;
- the final entity does not exist before the explicit application action;
- replaying the action cannot apply the same proposal twice;
- another user's proposal remains inaccessible.

Delivered result:

- The consumer API now exposes an owner-scoped proposal list, detail and explicit
  approve, reject, cancel and apply actions. The server returns action capabilities;
  React Native does not infer allowed mutations from status alone.
- Approval and application remain separate. Approval records review without
  creating an entity; application delegates to the existing safe create-Meal or
  create-DailyPlan command and returns the resulting trusted library identity.
- External/manual subject proposals retain the existing PPK warning and require an
  explicit acknowledgement before application.
- The mobile `Propuestas` center provides pending/applied/rejected filtering,
  bounded typed facts, nutrition previews, confirmations and navigation to the
  created Meal or DailyPlan.
- Navigation exposes Proposals only after its route became functional, and Today
  shows a pending proposal entry point without blocking the daily-plan flow.
- Ownership, separated approval/application, replay safety and external-subject
  acknowledgement are covered by focused API tests.
- Validation passed with 23 mobile API tests, strict TypeScript, Expo lint,
  18 mobile tests and a 29-route Expo web export.

### MCE04 — Comparator

Status: completed.

Goal: expose real comparison capability before the Assistant links to it.

Backend/API:

- add supported-kind metadata for Foods, Meals and DailyPlans;
- expose searchable selectable items through existing owner/visibility rules;
- add a dynamic compare endpoint that accepts two or more typed selections;
- normalize Food quantities with the established 100 g fallback and reject
  quantities for entity kinds that do not use them;
- project the same ordered web metrics and relative bars: calories, PPK when
  applicable, macro grams and P/C/F percentages;
- expose saved comparison list/detail;
- expose save/update only through existing saved-comparison commands and snapshot
  builders.

React Native:

- add kind selection, entity search and at least two comparison slots;
- add gram editing for Food slots;
- render metric-first comparison blocks with relative bars usable on iPhone widths;
- link every row back to its entity library detail;
- support saved comparison list/detail and saving the current result when the API
  capability is available;
- provide `Usar en el Asistente` as typed navigation context, not copied prose.

Exit evidence:

- comparable values match the existing comparison service output;
- saved comparison detail renders its stored snapshot rather than silently
  recalculating historical values;
- Programs cannot be sent as a comparison kind;
- fewer than two valid selections produce a clear validation state.

Delivered result:

- The consumer API exposes supported-kind metadata, owner-scoped searchable
  options, dynamic comparison, and saved comparison list/detail/create/update for
  Foods, Meals and DailyPlans. Programs remain outside the accepted contract.
- All calculations delegate to the existing comparison nutrition services and web
  metric viewmodel. Food slots use the established 100 g fallback; Meals and
  DailyPlans reject quantities and include PPK when a current weight is available.
- Saved writes delegate to the established saved-comparison commands and snapshot
  builder. Detail reads use `snapshot_payload`, so later source edits do not
  silently rewrite historical names or values; editing explicitly recalculates and
  replaces the snapshot only when the user saves.
- The mobile `Comparador` now preserves the web interaction model: two initial
  positional slots, explicit add/remove, per-slot search, repeated entities with
  different Food quantities, and metric-first relative bars. Every bar links back
  to the trusted library detail route.
- Saved comparisons have a native list and historical detail. A saved result can
  be reopened for editing with current source values, compared again and saved
  through the update command.
- Navigation exposes Comparator only now that its routes and API are functional.
  `Usar en el Asistente` remains intentionally unexposed until MCE05 provides a
  real Assistant route; MCE06 will add the typed navigation context without a dead
  link or copied prose.
- Ownership, repeated Food slots, 100 g fallback, relative bar output, non-Food
  quantity rejection and immutable snapshot behavior are covered by focused API
  tests. A mobile parity regression protects slots and metric-first rendering.
- Validation passed after the parity correction with 25 mobile API tests, strict
  TypeScript, Expo lint, 19 mobile tests and a 32-route Expo web export.

### MCE05 — AI chat history and durable turn transport

Status: completed.

Goal: make the existing async Assistant contract a complete mobile conversation
surface.

Backend/API:

- keep `POST /api/v1/ai/turns` and `GET /api/v1/ai/jobs/{job_id}` as the durable
  submit/poll path;
- add owner-scoped chat history list, chat detail and explicit new-chat semantics;
- return a versioned mobile conversation projection rather than an untyped copy of
  `conversation_payload`;
- expose capability/availability, credit and retry state required by the UI;
- preserve one serialized lane per chat and idempotent turn submission.

React Native:

- add chat list, new chat and resumed thread routes;
- render user/assistant messages with pending, retryable failure and completed states;
- poll using server `retry_after_ms` and recover a pending job after navigation or
  app suspension when local state still knows the job id;
- prevent double-send while one turn for the chat is pending;
- show bounded rate-limit, credit and provider-unavailable feedback;
- keep the composer usable with keyboard and safe-area insets.

Exit evidence:

- a new conversation persists and appears in history;
- a resumed chat sends its existing `chat_id` and retains prior state;
- submitting the same idempotency key cannot create two turns;
- closing and reopening the screen does not require resubmitting a completed job.

Delivered result:

- The consumer API exposes owner-scoped chat history and detail projections through
  `GET /ai/chats` and `GET /ai/chats/{chat_id}`. It emits bounded user/assistant
  messages and safe summary metadata; `conversation_payload`, brief internals and
  raw provider/job results never become the mobile contract.
- The existing `POST /ai/turns` and `GET /ai/jobs/{job_id}` durable path remains
  authoritative. A completed poll now returns only the trusted chat identity and
  refresh flags, after verifying that the persisted chat belongs to the user.
- Pending jobs are projected by the list/detail endpoints. Opening or reopening a
  new or existing chat resumes polling the server-reported job without submitting
  the turn again.
- The server enforces one pending turn per new-chat/user lane or existing-chat lane.
  A second idempotency key receives `assistant_turn_pending` instead of creating a
  concurrent turn; replay of the same key remains governed by the existing durable
  idempotency constraint.
- The mobile `Asistente AI` provides history, new and resumed conversation routes,
  bounded message rendering, server-derived availability/credit context, a
  multiline composer and pending/error feedback. Polling uses server retry timing,
  aborts on unmount and redirects a completed new turn to its persisted chat.
- Structured message presence is preserved but rendered as a safe notice in MCE05;
  MCE06 will project and render each supported typed product object.
- Navigation exposes Assistant only after all three routes became functional.
- Ownership, bounded projection, pending recovery and duplicate-turn blocking are
  covered by API/mobile regressions.
- Validation passed with 26 mobile API tests, strict TypeScript, Expo lint,
  21 mobile tests and a 35-route Expo web export.

### MCE06 — Typed chat objects and trusted actions

Goal: ensure Assistant outcomes are functional product objects, not decorative
assistant text.

- Define a discriminated mobile card union for:
  - profile draft;
  - preference draft;
  - proposal preferences;
  - proposal review;
  - saved comparison;
  - prepared action;
  - generated-plan compatibility card when still emitted.
- Render known card types with existing mobile entity/nutrition primitives.
- Ignore unknown card types safely while preserving surrounding message text.
- Link proposal cards to the MCE03 proposal detail.
- Link saved-comparison cards to the MCE04 saved detail.
- Link entity references to library details and calendarization references to
  MCE02.
- Add prepared-action commit/cancel endpoints and UI only when the server returns a
  trusted, owner-scoped, unexpired action. The provider never receives commit
  authority.
- Refresh the affected trusted surface after a successful action rather than
  assuming success from assistant copy.

Exit evidence:

- every in-scope card has a useful mobile destination or explicit trusted action;
- provider text alone cannot approve/apply a proposal or commit an action;
- unknown/expired cards fail closed without breaking the thread;
- cards remain visible after reopening persisted history.

Delivered 2026-08-13:

- persisted conversation objects are projected through a bounded typed union;
- proposal and saved-comparison cards navigate to their native trusted details;
- prepared actions resolve again against the authenticated owner, require an
  explicit native confirmation and refresh the chat after commit/cancel;
- unknown objects and unavailable actions fail closed without exposing raw
  conversation, provider or mutation payloads;
- API, TypeScript, lint and mobile test gates are green. MCE07 is next.

### MCE07 — Integrated journey, resilience and product polish

Goal: prove the capabilities behave as one product.

- Complete the journey Assistant -> Proposal -> Apply -> Library entity.
- Complete Program library -> Calendarize -> My Program -> Today.
- Complete Comparator -> saved result -> Assistant context -> returned comparison
  card.
- Refresh Home pending-proposal/program state after returning from mutations.
- Verify screen-reader labels, touch targets, keyboard behavior and narrow iPhone
  layout.
- Verify empty states for no Program, no proposal, no comparison and no chat.
- Verify 401 refresh, 403 entitlement, 404 ownership, 409 idempotency/conflict,
  422 validation, 429 rate limit and 503 AI-unavailable behavior.
- Sanitize observability and ensure no prompts, tokens, photos, raw OCR or private
  API payloads enter crash reports.

Exit evidence:

- the integrated journeys complete without a web handoff;
- a failed async turn does not discard the existing conversation;
- a failed domain mutation leaves server state unchanged and the screen retryable;
- navigation never lands on a route with no backing contract.

Delivered 2026-08-13:

- Assistant proposals apply into a native library destination and all involved
  screens refresh on focus;
- Program library selection, activation, My Program and Today form one native
  round trip;
- a saved comparison can enter a new Assistant turn through an owner-scoped ID,
  bounded product context and a persisted returned comparison card—never copied
  into user prose;
- Home refreshes program/proposal state on focus, and the main empty/error states
  remain retryable;
- stable mobile messages cover authentication, authorization, ownership,
  conflict, validation, rate limiting and temporary AI availability;
- shared controls retain at least 48-point touch targets, selectors carry screen
  reader labels and scrollable screens preserve keyboard taps;
- crash reporting continues to remove user, request, breadcrumb data, screenshots
  and view hierarchy. MCE08 is next.

### MCE08 — Confidence, documentation and closure

Goal: finish the day with reproducible repository evidence.

- Regenerate and commit the mobile OpenAPI contract.
- Add/extend backend tests for every new read/write endpoint, ownership boundary,
  stable error and idempotent action.
- Add mobile tests for types/contracts, navigation, async polling and card routing.
- Run mobile lint, strict TypeScript, Node tests and Expo web export.
- Run Django checks, focused mobile API/proposal/comparison/calendarization/AI tests
  and the repository fast gate.
- Run the full Django suite if the focused and fast gates are green within the
  working-day window; otherwise record it as the immediate post-cycle CI gate
  without claiming full-suite closure.
- Update current feature/API docs for stable shipped behavior and add a durable
  decision only where this cycle introduces a new architectural contract.
- Mark this cycle completed only with the evidence table filled.

Exit evidence:

- generated OpenAPI and committed schemas agree;
- all mandatory focused/fast/mobile gates are green;
- no placeholder route or TODO is counted as delivered behavior;
- remaining external gates are named explicitly.

## Planned API/screen matrix

Exact paths may be normalized during MCE00, but resource ownership and actions must
remain equivalent.

| Product area | Mobile API capability | React Native surface |
| --- | --- | --- |
| My Program | current calendarization, days, day detail, history | `/program` and `/program/days/[id]` |
| Activate Program | activate owned Program with confirmations | `/program/activate` or Program detail action |
| Program lifecycle | pause, resume, cancel, reminder preferences | `/program` |
| Proposals | list, detail, approve, reject, cancel, apply | `/proposals` and `/proposals/[id]` |
| Comparator | kinds, selections, compare, saved list/detail/save | `/comparator` and `/comparator/saved/[id]` |
| Assistant | chat list/detail/new, submit turn, poll job | `/assistant` and `/assistant/[id]` |
| Prepared actions | owner-scoped commit/cancel | rendered inside `/assistant/[id]` |

## Day plan and checkpoints

The cycle is executed as completion checkpoints rather than calendar promises.
Optional polish is cut before any invariant or required vertical is cut.

| Checkpoint | Patches | Required result |
| --- | --- | --- |
| Start | MCE00-MCE01 | Safe baseline, routes, types and navigation compile. |
| Checkpoint 1 | MCE02 | Program can be calendarized and appears in Today. |
| Checkpoint 2 | MCE03 | Proposal can be reviewed and applied safely. |
| Checkpoint 3 | MCE04 | Two or more supported entities can be compared. |
| Checkpoint 4 | MCE05-MCE06 | Durable chat renders typed actionable cards. |
| Close | MCE07-MCE08 | Integrated journeys and mandatory gates are green. |

## Priority and cut policy

If implementation pressure appears during the day, reduce scope in this order:

1. defer saved-comparison rename/edit polish while retaining dynamic comparison;
2. defer calendarization history polish while retaining activation and current
   program management;
3. defer non-essential chat card decoration while retaining typed cards and links;
4. defer animation and secondary visual refinements;
5. defer the local full Django suite to CI only after focused, fast and mobile
   gates pass.

The following cannot be cut while claiming the cycle complete:

- mobile calendarization activation;
- proposal review plus explicit application;
- dynamic comparison of all three supported kinds;
- persistent/resumable AI chat;
- typed proposal card routing;
- ownership, confirmation, idempotency and stable error tests;
- OpenAPI, TypeScript and mandatory focused checks.

## Acceptance criteria

- A user can calendarize an owned Program without leaving the app.
- Today resolves the newly active calendarization and its daily snapshot.
- A user can review, approve and apply an AI proposal without a web handoff.
- No AI message or provider-callable tool directly applies final nutrition state.
- A user can compare Foods with quantities and compare Meals/DailyPlans without
  quantities using server-authoritative calculations.
- A user can create or resume a durable Assistant chat and recover async state.
- Proposal and comparison cards open their trusted mobile surfaces.
- Unsupported or stale typed objects fail closed.
- Every new resource is owner-scoped and every mutation requires the correct mobile
  scope.
- The complete journey is protected by focused backend and mobile contract tests.

## Validation evidence

```text
Baseline/pre-existing failures                  -> none in mandatory mobile baseline
Django checks                                   -> passed, 0 issues
Migration drift                                 -> passed, no changes detected
Generated mobile OpenAPI                        -> passed, contract current
Focused calendarization/proposal/comparison/AI  -> passed, 366 tests
Repository fast gate                            -> passed, 95 tests plus hygiene/contracts
Complete Django suite                           -> passed, 1,770 tests in 276.460s
Mobile unified check                            -> passed
Mobile lint                                     -> passed, 0 warnings
Mobile strict TypeScript                        -> passed
Mobile Node tests                               -> passed, 24 tests
Expo web export                                 -> passed, 35 static routes
Integrated repository smoke                     -> passed, build plus 4 Node tests
Focused Ruff and diff hygiene                   -> passed
Physical iPhone smoke                           -> external gate
```

## Completion statement

MCE00-MCE08 ships native, contract-backed surfaces for Program calendarization,
Today execution, proposal review/application, Food/Meal/DailyPlan comparison and
durable Assistant conversations. The typed chat contract supports profile,
preference and proposal-preference drafts, proposal review, generated plans,
saved comparisons and trusted prepared actions. The integrated journeys complete
without a web handoff and every mutation remains owner-scoped, explicitly
confirmed and server-authoritative.

No declared product vertical was cut. Repository validation is complete; physical
iPhone interaction, notification delivery in the target environment and store
distribution remain operational/external rollout gates rather than repository
completion criteria.
