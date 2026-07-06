# 0066 · Admin Analytics export scope

Status: accepted
Date: 2026-07-04

## Context

After ADM10.1 and ADM10.2, Admin Analytics became an independent strategic console
with its own shell, navigation and compact filter bar. Further iterations are expected
to be mostly visual and structural: dashboard spacing, cards, tables, health signals,
responsive polish and navigation ergonomics.

Using the `full` export for these iterations is unnecessarily noisy because it includes
large portions of the product that are not needed to reason about the Admin Analytics
surface.

## Decision

Add a focused ChatGPT export mode:

```bash
./scripts/export_for_chatgpt.sh adminanalytics
```

The generated artifact is:

```text
../proyecto_django_export_adminanalytics.zip
```

The mode uses an allowlist and includes:

```text
admin_analytics/**
notas/static/notas/css/components/admin_analytics.css
scripts/export_for_chatgpt.sh
docs/current/operations/export_for_chatgpt.md
docs/current/design/ui_system.md
docs/current/architecture/ui_patterns.md
docs/planning/product_intelligence_admin_analytics_cycle.md
docs/decisions/*admin-analytics*
minimal Django project context
minimal source model context for dashboard selectors
```

It excludes broad user-facing templates, datasets, generated files, local databases,
large assets and unrelated product surfaces.

## Consequences

- Future UI and shell work on Admin Analytics can use a much smaller ZIP.
- The focused export preserves enough context to modify dashboard templates, CSS,
  filters, viewmodels, selectors and services.
- Changes that touch cross-app business behavior, settings beyond dashboard wiring,
  new models or broad regression tests should still use `full`.
- `planning` remains the right mode for documentation-only strategy work.

