# 0186 - Shared UI recipes and platform galleries

Status: accepted
Date: 2026-08-19

## Context

The Expo UI Gallery rendered production React Native components, but its browser
output was easy to confuse with the Django web product. Foundations were shared
through generated tokens while component geometry, variants and adapters could
still diverge. Dash KPI exposed the failure mode: the canonical component was
correct, but a library adapter selected a compact density outside the gallery.

## Decision

My Scoope adopts one semantic UI System with two authoritative implementation
galleries:

- Django templates and product CSS at `/app/dev/ui-system/` for desktop and
  mobile web;
- React Native production components at `/dev/ui-gallery` for iOS and Android.

`design/ui-contract.json` remains the neutral source for foundations and now
also owns platform-specific component recipes. The generator emits CSS custom
properties and TypeScript recipe values. It does not generate HTML or JSX.

Dash KPI is the pilot recipe. Native library screens consume the same public
components as the Native gallery. Duplicate library implementations of
`EntityCard`, `NutritionEntityCard` and `EntityDetailPage` are removed.

## Consequences

- Opening the Expo gallery in a browser is explicitly a Native preview, not a
  validation of Django CSS.
- Web gallery examples must include production partials rather than copied HTML.
- Native gallery examples and product routes must import the same public
  components.
- Component variants use semantic context names such as `regular` and `nested`.
- `npm run check:ui` rejects stale generated output and known duplicate or
  bypass paths.
- Additional component recipes migrate incrementally after Dash KPI proves the
  contract; a big-bang generation of CSS and React Native structure is avoided.
