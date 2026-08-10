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

## Explicit platform differences

Shared spacing, radii, typography, nutrition and entity semantics live under
`shared` in the contract. A difference must be recorded under `platforms.web`
or `platforms.native`; it must not be introduced in a generated file. Current
examples are the web spacing aliases used by legacy CSS and the brighter native
`dailyPlan` accent.
