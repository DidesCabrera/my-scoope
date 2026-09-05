# Web Composition Pickers

## Purpose

The editable web detail pages use composition pickers to add a Food to a Meal
and a reusable Meal to a DailyPlan. These pickers are modal journeys so their
content never changes the layout or scroll position of the detail page beneath
them.

## Supported journeys

### Food into Meal

1. “Agregar alimento” opens the picker on **Selección**.
2. The user can search the available Food library or choose **Crear alimento**.
3. Choosing a Food advances to **Impacto**.
4. The user adjusts the portion and sees the resulting Meal nutrition before
   submitting.
5. Creating a Food through this entry point returns to the originating Meal and
   opens the new Food directly on **Impacto**.

The same modal supports editing an existing MealFood relation. Edit opens on
**Impacto**, subtracts the original portion before calculating the preview, and
submits to the established relation update endpoint.

### Meal into DailyPlan

1. “Agregar comida” opens the picker on **Selección**.
2. The user can search reusable Meals or choose **Crear comida**.
3. Choosing a Meal advances to **Impacto**.
4. The user can define hour and optional note and sees the resulting DailyPlan
   nutrition before submitting.

Meal creation retains the pending-DailyPlan workflow: the new Meal is completed
with its Foods first, then the user returns to the originating DailyPlan picker.
Replacing an existing DailyPlanMeal snapshot opens the modal on **Impacto** with
its current schedule metadata and subtracts the original snapshot nutrition
before previewing the replacement.

## Interaction contract

- The modal uses the browser's top layer and therefore contributes no height to
  the detail document.
- Only one step is exposed at a time. “Cambiar selección” returns from Impacto to
  Selección without submitting.
- Both steps use the same padded scroll region and a shared, non-scrolling action
  footer. Cancel remains available after returning to Selección, and primary and
  secondary actions use the same visual contract in both picker types.
- The dialog keeps one responsive height across both states. In Impacto, its
  heading remains fixed while the selected item, contextual controls, and
  nutrition impact scroll inside `picker-layout`.
- DailyPlan Meal Impacto places Hora and Nota between the selected Meal and day
  impact, using the same contextual-control treatment as Food quantity.
- Impacto presents a projected UI-system `entity-card` instead of an isolated
  KPI preview: Food selection produces the resulting Meal card and Meal
  selection produces the resulting DailyPlan card. Each card includes the
  current children, highlights the pending addition or replacement, and updates
  projected nutrition totals before submission.
- Result cards reuse the production card anatomy (`card-title-comp`,
  `dash-kpi-comp`, responsive tabs and data grids). Meal projections expose the
  Alimentos, Tabla Alimentos, Calorías, Macros and Alloc panels; DailyPlan
  projections expose Menú, Tabla Nutricional, Calorías, Macros and Alloc.
- Every projected table row recalculates `% Cal`, intrinsic P|C|F distribution
  and macro allocation against the resulting entity. Quantity, selected Meal,
  Hora and Nota remain provisional until the user submits the fixed footer.
- `picker-layout` is a neutral scroll container with no padding, background,
  border or radius. The selected entity and its configuration form one standard
  `entity-card`: Food groups the selected Food with quantity, while Meal groups
  the selected Meal with Hora and Nota.
- Selected Food and Meal summaries preserve their picker-specific content but
  use the production card main anatomy: `entity-card__main` contains an
  `entity-card__title` column and an `entity-card__kpi` column. Source, unit and
  food aggregation remain secondary content below that main row.
- Selected titles use the production `entity-heading` hierarchy. Their eyebrow
  identifies `Alimento seleccionado` or `Comida seleccionada`, the entity name
  is the following `h3`, Food shows source/base badges, and Meal shows a live
  structural count of its foods.
- In Selección, the step heading owns the title, library/create actions, and
  search row as one fixed control region; only `selector-list` scrolls.
- Switching back to Selección removes any legacy inline display value from the
  inactive Impacto panel. Hidden step panels are always excluded from layout,
  so their heading and footer cannot remain visible between steps.
- The modal, its inner surface, and its fixed action footer use the shared
  `surface-card` token; the Impacto heading keeps its title and
  change-selection action on one row.
- Picker headers expose the current operation with a `plus` icon in add mode and
  a `repeat` icon in replace mode. Step headings are numbered `1.` and `2.`.
- The Meal impact step links directly to the selected Meal detail, using the URL
  supplied by the server payload rather than constructing a route in JavaScript.
- Both step headings share the same direct-heading structure and top origin, so
  their titles remain stationary during transitions. In Meal impact actions,
  `Editar comida` is the rightmost action.
- The direct `h3` occupies a shared 36px title row and centers its text
  vertically, matching the action-control height in either step.
- Step-heading titles use 12px of left inset without shifting the sibling
  actions or the rest of the heading content. Picker allocation indicators
  reuse the complete UI-system allocation track anatomy (`alloc-bar-bg`, fill,
  and overlay text) while preserving the compact 18px picker height.
- Food add/replace impact exposes only the resulting Meal's `Tabla Alimentos`
  tab and full food-table panel; redundant aggregation and mobile KPI-specific
  panels are omitted.
- Food quantity configuration sits directly below the fixed Impacto heading and
  outside `picker-layout`; only the selected/result cards scroll beneath it.
- Meal hour/note configuration follows the same fixed-region contract: it sits
  below the Impacto heading and outside the scrolling `picker-layout`.
- Fixed configuration controls align their leading icon with entity-card title
  content by deriving the left inset from the shared desktop/mobile card-padding
  tokens plus the title component's 4px internal inset.
- Modal step bodies keep horizontal inset but no bottom padding; spacing at the
  lower edge belongs to the fixed footer and the scrolling content itself.
- Food composition editing from a DailyPlanMeal uses the same two-step modal as
  direct Meal editing. Its fixed region contains the step heading and quantity;
  the scrolling region contains the selected Food plus projected Meal and
  DailyPlan UI-system cards. Existing add/update POST endpoints remain intact.
- The dialog is labelled by its visible title. Step progression is conveyed by
  the changing selection and impact content rather than a separate visual
  progress indicator.
- The trigger is a real button with `aria-haspopup="dialog"` and synchronized
  `aria-expanded` state.
- Escape, backdrop click, the header close button, and Cancel reset transient
  picker state, close the dialog, unlock page scrolling, and restore focus to
  the trigger.
- Search results and impact content scroll inside the dialog. At compact widths
  the dialog becomes a bottom sheet constrained to the viewport.

## Data and mutation boundaries

This UI does not introduce a new API or database model. Food search continues to
use the owner-aware Food picker JSON endpoint. Meal selection continues to use
the server-rendered picker payload. Nutrition previews remain client-side
projections of the established payloads, and final mutations continue through
the existing Django form endpoints and application commands.

Food creation accepts an optional `return_to` value only when Django considers
it safe for the current host. A successful picker-originated creation appends
the new `select_food` identifier to that safe URL. Missing or external return
destinations fall back to the Food library.

## Scope boundary

This contract applies to the canonical owned Meal and DailyPlan detail pages.
The DailyPlanMeal deep-edit Food picker remains an inline legacy surface, and
Program composition and the native client retain their own picker contracts.

## Verification

Coverage is split across:

- frontend source-contract tests for the shared dialog lifecycle and two steps;
- Django view tests for rendered modal structure and safe Food creation return;
- authenticated Playwright scenarios for add, edit, replace, cancel, search,
  reactive nutrition preview, submit, and absence of underlying layout shift.
