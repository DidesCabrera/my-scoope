# Consumer Product Brief

Status: current
Date: 2026-08-05
Audience: product, design, engineering and AI assistants

## Product direction

My Scoope is first a B2C product for people committed to achieving physical
change through precise nutrition planning, weighing food, following a program
and adjusting it from observed results.

The primary customer for the first mobile release is the person following their
own plan. Nutritionist workspaces, invited clients and seat purchasing are a
future expansion and must not shape the consumer mobile MVP.

## Core outcome

```text
define a physical goal
  -> build a nutrition program
  -> calendarize it on real dates
  -> follow planned meals and reminders
  -> record adherence and measurements
  -> review progress
  -> approve prospective adjustments
```

`Program` is the editable template. `ProgramCalendarization` is the lived
program: it owns the dated plan, reminders, execution evidence, measurement
context and future adjustment boundary. Past execution is never silently
rewritten.

## Initial goals

- fat loss;
- muscle gain;
- body recomposition.

My Scoope supports nutrition planning and informed self-management. It does not
diagnose, treat disease or replace medical advice.

## Consumer mobile MVP

The first React Native client covers:

1. registration, login and physical-goal onboarding;
2. Today, active program and calendarized-day detail;
3. planned meals, meal times, reminders and adherence check-ins;
4. weight measurements and progress trends;
5. foods, meals and daily plans needed by the active program;
6. on-device nutrition-label capture with explicit user confirmation;
7. AI Assistant over existing reviewable proposal boundaries;
8. subscription, privacy and account deletion.

The first release does not include nutritionist/client flows, seat purchases,
professional sharing, mobile administration, Android, barcode lookup, widgets,
Apple Watch, HealthKit writes, biometrics or a general-purpose offline mutation
queue.

## Experience principles

- The mobile app is a daily execution experience, not a view-for-view web port.
- Django remains the authority for nutrition, ownership and commercial rules.
- The client receives screen-oriented API contracts and does not reimplement
  domain calculations.
- Calendarization is the only active-program timeline.
- Users review OCR and AI results before persistent product changes.
- Denying camera, notification or future HealthKit permission never blocks the
  core planning experience.

## Visual direction

The existing UI system is real but partially implicit. The mobile client extracts
its established grammar instead of inventing another brand:

- dark semantic surfaces;
- cards as the principal composition unit;
- entity headers, nested child cards and macro summaries;
- badges, warnings, review states and clear primary/secondary actions;
- existing semantic entity and nutrition colors.

Web templates and CSS are not shared with React Native. The durable tokens,
hierarchy and domain components are translated into native primitives. Visual
continuity is required; pixel parity is not.

## Measurement

The MVP measures:

- onboarding completion;
- first program creation and activation;
- first calendarized day followed;
- first meal check-in and first weight measurement;
- first confirmed nutrition-label scan;
- weekly adherence;
- four-week retention;
- subscription conversion.

Feature completion without observable consumer use is not launch evidence.
