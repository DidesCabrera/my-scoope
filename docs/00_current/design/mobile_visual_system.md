# Mobile visual system

Status: current
Contract: `myscoope.visual-grammar.v1`

## Purpose

The React Native client translates the established My Scoope grammar instead of
sharing web CSS or copying web screens. The machine-readable contract is
`mobile/src/design/tokens.json`; React Native components consume it directly.

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
  -> Card (entity accent optional)
      -> nested muted Card
      -> MacroSummary
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
