# 0068 · Admin Analytics neutral dark theme

## Status

Accepted

## Date

2026-07-04

## Context

After ADM10.4, the Admin Analytics console had the right independent shell and page
hierarchy, but its visual identity still leaned on blue/black accents. For the V1
implementation closure, the console should feel more like an internal strategic system:
neutral, calm, dense and independent from the user-facing My Scoope visual language.

## Decision

Admin Analytics adopts a neutral dark theme as its base visual language.

The console keeps the same templates and information architecture, but its palette now
uses dark grays and blacks as the primary surfaces, with neutral gray accents instead of
blue accents. Status colors remain available only where they encode operational meaning
(for example warning or critical health signals).

## Consequences

- The console has a calmer, more internal-product identity.
- The UI no longer depends on blue accents for active navigation, icons or primary chrome.
- The strategic dashboard is visually separated from the normal My Scoope user app.
- No business logic, models or migrations are changed.
