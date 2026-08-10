# Mobile visual system

Status: current
Contract: `myscoope.visual-grammar.v2`

## Purpose

The React Native client translates the established My Scoope grammar instead of
sharing web CSS or copying web screens. The neutral machine-readable source is
`design/ui-contract.json`. `scripts/generate_ui_tokens.mjs` derives
`mobile/src/generated/ui-tokens.ts`, and application code consumes it through
the stable `mobile/src/design/tokens.ts` facade.

The same generation pass writes
`notas/static/notas/css/ui-contract.generated.css` for Django. Generated files
must not be edited by hand. `npm run generate:ui` refreshes them and
`npm run check:ui` rejects stale output.

## Foundations

- dark-first app canvas `#000000`;
- primary and nested card surfaces `#121212` and `#202020`;
- 22-point outer card radius with 16/12/8-point nested radii;
- 4/8/12/16/22/28-point spacing scale;
- system typography with explicit semantic sizes and native accessibility;
- semantic program, daily-plan, meal, food and nutrition colors inherited from
  the web token contract.

## Native hierarchy

```text
Screen
  -> AppHeader
  -> ContentPanel / EntityCard
      -> EntityHeading / DetailSection / PanelTabs
      -> nested muted Card
      -> MacroSummary / NutrientProgress / NutritionMetric
      -> KpiAllocationBar / PanelAllocationBar
      -> NutritionKpiSection / ProteinPerKilogramBadge
      -> Pill / InlineNotice
      -> Button / Field / ChoiceRow
```

Cards are the principal composition unit. Color communicates entity or nutrient
meaning; it is never the only state indicator. Press targets have a minimum
height near 44 points, text uses the system font and controls expose native
accessibility roles and states.

## Product application

- Login uses a sparse black canvas and one high-priority action card.
- Onboarding groups body data into one deliberate card rather than a long web
  form.
- Today makes the active calendarization the parent card, the daily plan the
  nutrition summary and meals nested child cards.
- Check-in preserves the meal-card hierarchy but cannot claim persistence before
  CML04 owns adherence.
- Weight uses a focused input card and a quiet chronological history.

Pixel parity with Django is not a goal. Semantic continuity, hierarchy and reuse
are required.

## Component boundaries

`mobile/src/components/ui/index.ts` is the only public UI import. Internally the
layer is divided into `layout`, `typography`, `controls`, `feedback`, `surfaces`
and `product`. Nutrition components have their own public barrel at
`mobile/src/components/nutrition/index.ts`.

The development-only route `/dev/ui-gallery` renders the shared components,
interaction states, entity palette, type sizes, spacing, radii and nutrition
widgets using production component code.

`KpiAllocationBar` and `PanelAllocationBar` share percentage normalization and
nutrition tones. KPI composition keeps the colored percentage cell next to its
track; panel composition overlays the value on the track and supports regular
and compact density. A future calories tone must extend the neutral token
contract and reuse these components rather than introduce a third bar.

`NutritionKpiSection` is the canonical composition of total calories, macro
grams, protein-per-kilogram and the three KPI allocation bars. It receives
already-computed presentation values and never recalculates domain nutrition.
Regular density belongs in main entity surfaces; compact density belongs in
nested cards and panels. `ProteinPerKilogramBadge` owns the reusable PPK label,
locale-aware formatting and accessible description.

Each macro KPI is a single horizontal row: short label, reserved PPK slot,
grams and allocation bar. Product copy uses `Carbos`; the formal
`carbohidratos` term remains only in label/OCR parsing rules for source-data
compatibility.

The shared scale includes `spacing.compact` (6 px) for layouts that need a
step between `xs` (4 px) and `sm` (8 px). Font weights also belong to the
contract (`regular`, `medium`, `semibold`, `bold`, `extraBold`, `black`): use
medium or semibold for compact supporting data, and reserve heavier weights
for hierarchy and emphasis.

Native UI uses the platform `System` family (SF Pro on iOS and Roboto on
Android); web uses the `system-ui` stack. Nutrition KPI labels use regular
weight, the calorie value uses bold, and the complete KPI composition keeps
neutral tracking (`letterSpacing: 0`).

`CalorieValue` owns the shared calorie-number typography used by both
`MacroSummary` and `NutritionKpiSection`. It uses extra-bold weight,
proportional figures and neutral tracking for a compact native display.
Tabular figures remain reserved for aligned grams, percentages and PPK data.

## Card headings

`CardHeader` is the generic heading inside a card or panel. Its regular title
uses 16 pt semibold text; its compact title uses 13 pt semibold text. Both use
neutral tracking, optional regular-weight descriptions and an optional trailing
accessory. `ContentPanel` uses the regular variant and `DetailSection` uses the
compact variant.

`SectionTitle` remains a screen-level section divider outside cards.
`EntityHeading` remains the branded heading for entity cards and owns the
entity icon, eyebrow and semantic color. Its composition follows the web:
entity icon plus eyebrow, entity name, then optional structural indicators.

`EntityIcon` maps semantic entity kinds to the shared Lucide vocabulary and
applies the entity color. `StructuralIndicators` is independent from the
heading and renders accessible value/icon pairs with automatic dividers; it
can therefore be reused in cards, detail headers and future picker results.
Entity icon vectors and structural-indicator content use explicit white
foreground tokens for contrast on native surfaces.

`NutritionEntityCard` is the reusable product composition of `EntityCard` and
`NutritionKpiSection`. It owns only the separator and spacing between those
sections; both the heading and KPI remain independently reusable.

## Entity panels

The native panel system mirrors the mobile Django information architecture
without copying desktop tables. `PanelSurface`, `EntityPanelTabs`, `PanelBody`
and `PanelEmptyState` own the shared interaction and surface contract.

`FoodPanels` is used by Meal and DPM entities and exposes `Alimentos`, `Macros`
and `Alloc`. `MealPanels` is used by DailyPlan and exposes `Menú`, `Macros` and
`Alloc`. Their content panels (`FoodQuantityPanel`, `MealMenuPanel`,
`NutritionMacrosPanel`, `NutritionAllocationPanel`) remain independently
reusable. Food has no nested panels in the current web contract. Program
panels and charts are intentionally excluded from this first stage.

`MealMenuPanel` follows the pre-existing mobile DailyPlan menu rather than the
desktop two-column table: each full-width cell starts with the Meal entity icon
and meal name, followed by a secondary enumeration of structured food
quantities such as `Avena (80g)`.

## Explicit platform differences

Shared spacing, radii, typography, nutrition and entity semantics live under
`shared` in the contract. A difference must be recorded under `platforms.web`
or `platforms.native`; it must not be introduced in a generated file. Current
examples are the web spacing aliases used by legacy CSS and the brighter native
`dailyPlan` accent.
