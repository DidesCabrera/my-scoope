# UIS10 — Selective CSS Loading Cycle

Status: completed
Date: 2026-07-19
Cycle code: UIS10

## Objective

Start reducing global feature CSS safely and make the first physical split of Programs styles.

## Delivered

- Added the `feature_css` template block at the former Programs position in the cascade.
- Removed `programs.css` from every non-Program page.
- Loaded `programs.css` explicitly in all seven Program page templates.
- Extracted Program week-tab composition to `program_week_tabs.css`, loaded only by Program detail.
- Removed the nonexistent `mobile_grid_tabs.js` reference; `collapse_cards.js` remains the canonical responsive panel controller.

## Acceptance

- Program pages retain feature styles in the same cascade region.
- Other pages no longer download the large Programs stylesheet.
- No duplicate mobile-tab controller is introduced.

