# Web Composition Picker Modal Cycle

Status: completed
Date: 2026-09-04
Cycle code: WCP00-WCP04

## Objective

Move the editable web composition pickers out of the document flow so opening
them never displaces the Meal or DailyPlan detail content. Align the journey
with the native client by making selection and nutrition impact two explicit
steps while preserving the established Django commands and nutrition math.

## Baseline

- Meal detail renders the Food picker inline between its section heading and
  comparison table.
- DailyPlan detail renders the Meal picker in the same inline position.
- Both surfaces expand by toggling `display`, so the table and all following
  content move when the picker opens or its preview appears.
- The native composition picker already separates library selection/creation
  from configuration and server-computed impact.
- Web Food impact is computed from the selected portion and current Meal; web
  Meal impact is computed from the selected Meal and current DailyPlan. This
  cycle keeps those calculations and submit endpoints unchanged.

## Scope

- Owned, editable Meal detail: select/create a Food, configure its portion,
  preview the Meal impact, and add or update the relation.
- Owned, editable DailyPlan detail: select/create a Meal, configure schedule
  metadata, preview the DailyPlan impact, and add or replace the snapshot.
- Shared modal behavior, responsive styles, focus/keyboard behavior, focused
  Django/JavaScript contracts, and authenticated browser scenarios.

The DailyPlanMeal deep-edit Food picker, Program pickers, native code, mobile API
contracts, and persisted nutrition data are outside this cycle.

## Patches

### WCP00 — Contract and inventory

- Record the inline-layout cause and the native two-step reference behavior.
- Freeze existing commands, form endpoints, ownership checks, and nutrition
  calculations as compatibility constraints.

### WCP01 — Shared modal shell

- Introduce one accessible native dialog contract for composition pickers.
- Keep the dialog in the browser top layer, constrain its viewport size, and
  give its result list and impact content independent scrolling.
- Support trigger, close button, backdrop, Escape, focus restoration, and page
  scroll locking.

### WCP02 — Explicit two-step journey

- Step 1 exposes library search/results and a create action.
- Selecting an item advances to step 2.
- Step 2 exposes selection configuration and its nutrition impact.
- “Cambiar selección” returns to step 1 without mutating the parent entity.
- Add/edit/replacement submissions retain the current server-side behavior.

### WCP03 — Creation handoff

- Food creation accepts an owner-safe return URL and returns the newly created
  Food to the originating Meal picker.
- Meal creation keeps the established pending-DailyPlan workflow and returns to
  the DailyPlan picker after the draft Meal is completed.

### WCP04 — Confidence and closure

- Cover modal structure, steps, creation handoff, and safe redirects with
  focused tests.
- Adapt picker browser scenarios and assert that opening the top-layer dialog
  does not move underlying detail content.
- Run focused Django and frontend suites, then the repository web checks.

## Acceptance

- Opening either picker does not change the position of the underlying detail
  table or other document-flow content.
- The dialog starts at “Selección”; choosing an item advances to “Impacto”.
- Each selection step contains search/results plus a relevant create action.
- Impact values still react to Food quantity or Meal scheduling inputs and the
  existing add/update forms submit the same payloads as before.
- Edit and replace actions open directly on the impact step with the current
  relation loaded.
- Escape, backdrop, header close, and visible cancel actions close the dialog,
  reset transient state, and return focus to the trigger.
- Invalid external return URLs cannot be used by Food creation.
- No database migration or mobile API change is introduced.

## Risk and rollback

The main risks are regressions in edit-mode initialization, focus handling, and
the Food creation return path. The dialog wraps the existing picker markup and
domain scripts instead of replacing commands or math, while focused tests retain
the existing form and payload contracts. Rollback is limited to templates,
styles, browser scripts, tests, and documentation.

## Delivered

- Replaced the inline Meal Food and DailyPlan Meal picker containers with a
  shared native-dialog contract that stays outside document layout.
- Added explicit Selección and Impacto steps, visible progress, library/create
  entry actions, “Cambiar selección”, internal scrolling, and a compact bottom
  sheet presentation.
- Preserved Food quantity math, Meal/DailyPlan impact math, add/update endpoints,
  edit and replacement initialization, and the legacy inline DailyPlanMeal Food
  picker.
- Restored the hour and optional note inputs already supported by the Meal picker
  script and server command to the visible Impacto step.
- Added a safe Food creation return that opens the newly created Food in the
  originating Meal impact step; same-host validation prevents external redirects.
- Added current feature documentation plus frontend, Django, desktop browser, and
  compact-viewport coverage.

## Validation evidence

```text
Frontend unit/source contracts                -> 7 passed
Focused Django picker/view contracts          -> 86 passed
Repository fast checks                        -> passed (96 tests)
Existing authenticated picker browser suite   -> 23 passed
Compact 390x844 modal browser scenario        -> passed
Post-CSS-split desktop/mobile browser smoke    -> 3 passed
Django system and migration checks            -> passed; no migration generated
UI architecture and document registry         -> valid
```

Browser validation used a disposable migrated SQLite database and deterministic
E2E fixtures. No developer database or active worktree data was modified.
