# Mobile Composition Pickers

## Purpose

The native application uses a shared two-step flow to add or replace a Food in
a Meal, a Meal in a DailyPlan, and a DailyPlan in a Program week:

1. select or create an entity from the owner's library;
2. configure the relation and review the server-projected result before commit.

Each step has its own route. The native back action returns from configuration
to selection, so result cards do not duplicate a “Cambiar selección” action.

## Configuration contract

- The selected entity scrolls away, while the configuration card remains fixed
  below the native header.
- Food configuration presents a compact, right-aligned portion input with the
  same scale icon used by web.
- Meal configuration presents a compact, right-aligned time input, a divider,
  and a collapsed optional note. The pencil action reveals the note input.
- Program configuration presents all seven compact day controls in one row.
- Scale, clock, notebook and calendar icons identify portion, time, note and
  weekday configuration without requiring a redundant section title.

Configuration changes are debounced and refresh the projection without
unmounting the current result. A small activity indicator beside
“Previsualización del impacto” communicates the refresh. Commit remains disabled
until the rendered preview belongs to the exact current payload; a stale preview
can therefore remain visible safely while quantity or weekdays change.

## Projected-result contract

Preview endpoints are owner-scoped and read-only. They return a typed `result`
whose nutrition and structural data is calculated by the server. The native
client must not reproduce calories, macros, allocation or PPK calculations.

- Food-to-Meal renders the resulting Meal with its Food panels.
- When Food is edited inside a DailyPlanMeal, the request carries the enclosing
  DailyPlan and DailyPlanMeal identifiers. The response renders both the
  resulting Meal and resulting DailyPlan cards.
- Meal-to-DailyPlan renders the resulting DailyPlan with its Meal panels,
  including configured time and note.
- DailyPlan-to-Program renders the projected week title and seven-day comparison
  table. Its impact card intentionally omits the nutrition KPI block because the
  comparison table is the authoritative visualization at this level.
- Projected rows distinguish additions and replacements. Program assignment
  continues to require explicit confirmation when occupied days are replaced.

## Mutation and navigation boundaries

Commit endpoints continue to delegate to the established domain commands.
Preview data never creates relations, and newly projected rows do not expose a
persisted relation identifier. Food replacement from a DailyPlan context
preserves enough route context to return to the originating detail screen.

The confirmation action is available only when configuration is valid, no
preview request is active, and the latest successful preview key matches the
current payload key.

## Verification

The contract is covered by:

- `mobile/tests/composition-pickers.test.ts` for routes, fixed configuration,
  refresh behavior, result-card anatomy and contextual navigation;
- `mobile_api/tests/test_composition_projections_api.py` for projection content,
  ownership and contextual Food editing;
- the committed `docs/00_current/api/mobile-v1.openapi.json` schema.

Physical-device and simulator smoke tests remain appropriate for touch, sticky
layout and production-sized scrolling behavior.
