# 0157 - UI Anatomy and Selective Program CSS

Status: accepted
Date: 2026-07-19

## Context

Headings, collection empty states and message-like cards repeated the same anatomy under feature-specific names. In addition, `programs.css` loaded on every authenticated page and `base.html` referenced a `mobile_grid_tabs.js` file that does not exist in the repository or its history.

`collapse_cards.js` already owns responsive panel selection, configured defaults, active state, query-string selection and breakpoint changes.

## Decision

1. Adopt neutral `entity-heading`, `collection-*` and `message-card` contracts while retaining legacy aliases during migration.
2. Load Programs CSS only through the `feature_css` block on Program pages.
3. Extract week-tab composition to `program_week_tabs.css` and load it only on Program detail.
4. Remove the obsolete `mobile_grid_tabs.js` script tag. Do not create a second controller or an empty compatibility file.

## Consequences

- Programs remains visually aligned with other entities while its domain composition stays isolated.
- Non-Program pages avoid a large unrelated stylesheet.
- The panel behavior has one canonical JavaScript owner.
- Further feature styles can move to selective loading in later, independently testable slices.
