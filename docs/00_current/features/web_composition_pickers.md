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
  heading and optional schedule fields remain fixed while the stacked selected
  item and nutrition impact sections scroll inside `picker-layout`.
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
