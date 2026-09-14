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
      -> WeekDayGrid / WeekDayCell
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

The development-only route `/dev/ui-gallery` is the Native UI Gallery and renders the shared components,
interaction states, entity palette, type sizes, spacing, radii and nutrition
widgets using production component code. Its browser rendering is an Expo/
`react-native-web` preview; the Django/CSS system is validated separately at
`/app/dev/ui-system/`.

`WeekDayGrid` and `WeekDayCell` own the shared seven-column weekly layout used by
Today and Program. Below 350 pt of available content width the grid reduces its
gap from 6 pt to 4 pt; Today's date circles also reduce from 44 pt to 40 pt while
preserving the 13 pt date and 9 pt month typography. Both contexts use 44 pt
circles, 40 pt in compact layouts, 1 pt borders and the same multicolor selection
ring. The selection ring preserves a narrow neutral gap around the circle so its
state does not merge visually with the filled surface. Interactive Program circles
retain a 44 pt effective touch target. The Native UI Gallery's
Calendars section renders both production components inside 414 pt and 375 pt
device frames so their responsive geometry can be compared in the browser.

“Mi programa activo” uses the dated hybrid of those two recipes: chronological
`calendar_date` determines the visible weekday order, every circle shows day and
three-letter month, and an empty editable future date carries a small add affordance.
It therefore may begin on any weekday. Filled future dates retain an explicit action
to replace their DailyPlan; present and past dates remain historical and non-editable.
When a week becomes active in the UI, its first chronological program day is selected
by default; the current week instead selects today's dated slot. Today uses the same
white-filled circle as Home. An empty selected slot renders an explicit “Día sin plan”
state rather than leaving the plan-detail area blank.

`KpiAllocationBar` and `PanelAllocationBar` share percentage normalization and
nutrition tones and overlay the value on the track. Entity panels use the
regular 24 px bar; compact density remains available only for deliberately
dense secondary contexts. A future calories tone must extend the neutral token
contract and reuse these components rather than introduce a third bar.

`NutritionKpiSection` is the canonical composition of total calories, macro
grams, protein-per-kilogram and the three KPI allocation bars. It receives
already-computed presentation values and never recalculates domain nutrition.
The `regular` variant belongs in main entity surfaces; the semantic `nested`
variant belongs only in deliberately nested cards. `ProteinPerKilogramBadge` owns the reusable PPK label,
locale-aware formatting and accessible description.

The calorie surface is square in both KPI variants. Its geometry comes from the
generated `tokens.component.nutritionKpi` recipe: Native regular uses 96 pt,
3 pt border and 22 pt radius; Native nested uses 76 pt, 2 pt border and 16 pt
radius. Below 420 pt of available window width the regular composition switches
to 4 px macro-row padding and 22 px KPI bars; from 420 pt it uses 5 px and 24 px.
Nested keeps its 18 px bars. This responds to usable width rather than device names.

Each macro KPI is a single horizontal row: short label, reserved PPK slot,
grams and allocation bar. Product copy uses `Carbos`; the formal
`carbohidratos` term remains only in label/OCR parsing rules for source-data
compatibility. Labels, PPK, grams and allocation values use a unified 13 px
medium treatment from 420 pt of window width and a unified 12 px medium
treatment below 420 pt. This typography rule applies in both KPI variants.
The final `Grasas` row has no bottom separator.

KPI allocation bars use the same continuous filled-track presentation as
panel bars. KPI retains its original 6 px radius while panel bars use 4 px;
both tracks and their colored fills round the right edge consistently. The web
counterparts apply the same geometry through inherited fill radii.

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

`SectionHeading` is the canonical structural heading for a section. It combines
a title with optional structural detail (for example, an item count) and an
optional semantic icon; it is therefore more than a typographic H1/H2 style. It
uses 16 pt semibold type and owns the standard 8 px separation above section
boundaries.
`SectionTitle` remains only as a compatibility alias.
`EntityHeading` remains the branded heading for entity cards and owns the
entity icon, eyebrow and semantic color. Its composition follows the web:
entity icon plus eyebrow, entity name, then optional structural indicators.
Its `page` variant is reserved for extended page-cards: below 420 pt the entity
name uses 22 pt type with a 32 pt line height; at wider widths it uses 24/34.
The regular card variant keeps its existing 20/25 treatment.

`EntityIcon` maps semantic entity kinds to the shared Lucide vocabulary and
applies the entity color. Only Food, Meal, DailyPlan, DPM and Program use this
colored surface. Navigation and functional areas use `SectionIcon`; its
canonical Lucide glyphs render on a transparent background, and their complete
mapping is visible in the Tokens gallery. `StructuralIndicators` is independent from the
heading and renders accessible value/icon pairs with automatic dividers; it
can therefore be reused in cards, detail headers and future picker results.
Entity icon vectors and structural-indicator content use explicit white
foreground tokens for contrast on native surfaces.
Structural indicators may omit their icon when the structural value is already
self-describing, such as a Food nutrition basis of `100 g` or a named serving.
The gallery's complete Food card demonstrates this title + basis + KPI contract.

`CollectionPageHeader` is the canonical heading for list views on native and
matches Django's `list_page_header`. Its first row aligns a 40 px semantic
entity icon with a 12 px radius and a left-aligned 26/32 semibold collection title; structural item
information occupies a new left-aligned row below the icon. It uses
`StructuralIndicators` on native and the equivalent web indicator. It also accepts
an explicit icon or action for list views whose page identity differs from the
underlying entity. It must not be confused with `SectionHeading`, which labels
a section inside an existing page.

`NutritionEntityCard` is the reusable product composition of `EntityCard` and
`NutritionKpiSection`. The composition relies only on the card's standard gap:
it adds no separator or extra padding between heading and KPI. Both components
remain independently reusable, and standalone entity headings are unchanged.

## Entity panels

The native panel system mirrors the mobile Django information architecture
without copying desktop tables. `PanelSurface`, `EntityPanelTabs`, `PanelBody`
and `PanelEmptyState` own the shared interaction and surface contract.

`FoodPanels` is used by Meal and DPM entities and exposes `Alimentos`,
`Calorías`, `Macros`, `Dist` and `Alloc`. `MealPanels` is used by DailyPlan and
exposes `Menú`, `Calorías`, `Macros`, `Dist` and `Alloc`. Their content panels
(`FoodQuantityPanel`, `MealMenuPanel`, `NutritionCaloriesPanel`,
`NutritionMacrosPanel`, `NutritionDistributionPanel`, `NutritionAllocationPanel`) remain independently
reusable. The final data row in every panel omits its bottom separator. Food
has no nested panels in the current web contract. Program
panels and charts are intentionally excluded from this first stage.
Inactive panel tabs retain their standard border on both platforms. The active
tab keeps the same one-pixel geometry but uses a transparent border, avoiding a
second visible outline or a size change. Every grid header and item row owns 8
px of horizontal padding; panel bodies and grid wrappers do not add a second
horizontal inset around those rows. Menu headers and rows declare this inset
explicitly because their responsive layout has specialized rules.
`MealRowIdentity` is the shared native microcomponent for the Meal icon and meal
name; Django uses the equivalent `grid_meal_identity.html` partial. Menu, macro
and allocation panels reuse it in their meal-name column. Its 4 px internal
inset makes Menu identity content align with the first column in other panels.
The menu time and ingredient enumeration use that same 4 px internal inset.
Nutrition panels reserve a fixed leading column for the Food, Meal, day or week
identity. `Macros` places PpK immediately after that identity and then exposes
P/C/F grams without a distribution bar. `Dist` exposes the intrinsic P/C/F
calorie percentages and retains the stacked P/C/F distribution bar. `Alloc`
remains the contextual contribution of each row to its parent macro totals.
PpK uses the user's current weight and renders an unavailable marker when no
weight exists.

## Entity detail pages

`EntityDetailPage` is the reusable native detail-page composition. Its outer
surface is transparent and borderless, matching the web detail contract;
entity heading, KPI, subsequent sections and metadata share the app surface.
Internal cards and panels retain their own functional surfaces. `EntityDetailSection` pairs the shared
`SectionHeading` with reusable panel content, while `EntityDetailMetadata` provides the
initial creator/update footer. The gallery's `Detalle` tab demonstrates the
contract with a DailyPlan; food, meal and DPM routes can reuse the same shell
with entity-specific panels.

The detail composition preserves standard screen gutters without adding top
padding beyond the screen container. DailyPlan meal sequence markers mirror web: a numbered
circle sits over a horizontal divider above each meal card, consuming no
horizontal card space. Nested DPM meal cards use the standard card contract:
`card.outerPadding` (18 px) and `card.gap` (12 px). Their outer placement also
follows the page-card's content padding.

The gallery token tab exposes `card.outerPadding`, `card.innerPadding` and
`card.gap` alongside the spacing scale so card dimensions remain explicit.
`layout.reducedInset` is 12 px. Every standard `Card` expands by the full
`spacing.screen` gutter (currently -18 px per side), so its surface reaches both
viewport edges while its content retains `card.outerPadding`. Pressable entity
cards apply the same expansion to their touch target rather than only their
visual surface. Shared section dividers use the same full-screen expansion.
Other controls and the canonical `PanelSurface` retain the
reduced-inset calculation (`layout.reducedInset - card.outerPadding`, currently
-6 px per side) for panels, buttons, inputs, week-day grids and nested content.
`EntityCardPanelSlot` only provides layout containment. Negative margins are
owned by the card and panel primitives and must not be repeated manually in
consuming views.
Gallery navigation is adaptive and remains separate from product panel tabs:
below 700 pt it uses a compact dropdown above the examples to preserve card
width, and at 700 pt or wider it becomes a vertical sidebar to the left.

## Proposals

Proposals use a separate native family because review state, request summary,
attachments and human approval actions do not belong to normal entity cards.
`ProposalCard` is the inbox/list summary. `ProposalDetailPage` composes the
review hero, request context and proposed entities inside one full-bleed extended
page-card, matching the entity detail contract. The hero is not wrapped in a
second card, and the page-card reaches both viewport edges.
`ProposalReviewSection`,
`ProposalMetricGrid` and `ProposalReviewActions` cover validation content and
the approval/rejection/cancellation workflow. Proposed Meal or DailyPlan
content continues to reuse the existing entity cards inside that review shell.
Those entity cards retain their corresponding panels: the DailyPlan example
includes `MealPanels` with Menú, Macros and Alloc. The gallery's `Propuestas`
tab shows both levels.

`ChatProposalCard` is the compact third scale inserted in an assistant message
after a proposal request. It shows current/previous state, a short summary,
optional iteration labels, key comparison metrics and one explicit CTA into
the full review; it intentionally does not embed the complete entity card.

Proposal list-card and detail-page headings follow the entity title hierarchy:
a proposal icon sits beside the `Propuesta` eyebrow, followed by title and
received-date metadata. They do not use a detached top-right icon.

`ProposalRequestSummary` is the semantic block that presents what the user
requested together with the information and objectives used to evaluate the
proposal. It sits below a `Detalles de la propuesta` section heading and uses
the standard 18 px card padding. `ProposalObjectiveKpiSection` presents nutrition targets through the
canonical KPI composition, and `ProposalObjectiveSection` places it immediately
below the requirement copy in that same block. Technical intent identifiers are
not shown in the interface. `ProposalEntitySection` groups proposed entity
cards under the shared `SectionHeading`, using a white paperclip icon. Its
everyday title is derived from entity kind and count (`Plan propuesto`, `Planes
propuestos`, `Comida propuesta`, etc.). It has no
`Adjunto` eyebrow, nested card or redundant attachment-name pill. `ChatProposalCard`
reuses `ProposalCard`; `Lista para revisión`
is a status label, not a separate visual object type.

DailyPlan detail keeps the web hierarchy: the aggregated `MealPanels` section
is followed by `DailyPlanMealDetailList`. The latter renders an ordered meal
sequence and reuses `NutritionEntityCard` plus `FoodPanels` for every child
meal, rather than introducing a second child-card implementation.

`MealMenuPanel` follows the pre-existing mobile DailyPlan menu rather than the
desktop two-column table: each full-width cell starts with the Meal entity icon
and meal name, followed by a secondary enumeration of structured food
quantities such as `Avena (80g)`.
Panel bodies use the 4 px `xs` horizontal inset, and DailyPlan food
enumerations do not add a second left indent.

## Comparisons

The first native comparison family is derived from Django's comparator detail
and saved-list views. `ComparisonScopeTabs` switches among Food, Meal and
DailyPlan scopes through `DistributedTabBar`, the same full-width primitive used
by Assistant AI; its three tabs divide the available width evenly. On the saved
comparison lists, each scope tab owns its item count; the page heading does not
repeat that quantity in a detached chip. Once the large page heading scrolls,
`Comparador` becomes visible in the compact global header, matching the active
program list behavior, while its distributed scope tabs remain pinned beneath
that header. The UI-System's
`ScrollableTabBar` remains the intrinsic-width alternative for collections such
as program weeks. Labels, optional icons and counts are centered as one group in
both tab-bar components. `ComparisonSelectionCard` represents a numbered selection and
its optional quantity/removal action in read mode. `ComparisonBuilder` groups
editable `ComparisonEditorCard` instances with add, save and compare actions;
each editor owns the entity selector and, where applicable, quantity input.
Editable selections never render a separate numbered heading. Their
position-aware field label (`Alimento 1`) and selector are the complete identity;
once selected, the entity icon appears inside the selector beside its name.
Selected and saved comparison identities always render quantity inline after
the entity name using the compact `(100g)` format; quantity is never a detached
right-aligned column.
Read-only and saved selections also omit the numbered circle. Position remains
available through the textual eyebrow (`Alimento 1`) above the entity identity.
An optional removal action sits beside the selected input and does not recreate
a detached title section.
The builder identifies itself with the canonical transparent Comparator section
icon (`columns-3`) and the `Nueva comparación` eyebrow.
Builder actions reuse the canonical `Button` component also used by proposal
review: Compare is primary, while Add and Save are secondary actions.
Editable selection cards use the standard reduced 12 px nested-card inset by
expanding horizontally from the builder's 18 px content padding.
The builder uses the dark card surface; editable selections use the lighter
muted surface, with dark input surfaces nested inside them.
`ComparisonMetricCard` presents one
metric and receives already-normalized bar widths rather than recalculating
domain values. Its parallel `compactAlloc` variant reuses `PanelAllocationBar`
at compact height with its interior value hidden; the continuous variant remains
the default. `SavedComparisonCard` composes a comparison heading, canonical
structural count and the existing `FoodPanels` component. Its tabs are
Alimentos, Macros and Alloc, and its rows are the compared foods rather than a
detached preview string. The extended
`SavedComparisonDetailPage` follows the full-bleed page-card contract and owns
the saved-comparison heading, entity count, read-only selections, comparative
results and optional edit action.
Its title count is rendered by the canonical `StructuralIndicators` component,
including the white structural entity glyph rather than a colored entity icon.
The gallery demonstrates these contracts with a Food comparison; live selector
data, persistence, rename/delete and advanced saved-detail actions remain
outside this first visual iteration.

## Explicit platform differences

Shared spacing, radii, typography, nutrition and entity semantics live under
`shared` in the contract. A difference must be recorded under `platforms.web`
or `platforms.native`; it must not be introduced in a generated file. Current
examples are the web spacing aliases used by legacy CSS and the brighter native
`dailyPlan` accent.
