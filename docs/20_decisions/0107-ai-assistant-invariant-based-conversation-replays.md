# 0107 — AI Assistant invariant-based conversation replays

Status: accepted
Date: 2026-07-13
Scope: fake-provider conversation harness, replay diagnostics and LLM-native regression coverage

## Context

The original scripted replay harness was useful for exercising the real provider envelope parser, tool loop, `NutritionBrief` synchronization and card renderer. However, its main regression test also encoded one exact conversation choreography:

```text
greeting -> request -> goal -> profile choice -> age -> sex -> activity -> meals -> style
```

Assertions depended on concrete turn indexes such as the fourth, sixth or eighth turn. That made a harmless change in phrasing, grouping or ordering look like a product regression, even when the resulting state and product behavior were correct.

After CM20 and CM21 removed deterministic interview policy from provider context and prompts, the replay suite must not reintroduce that same rigidity through tests.

## Decision

Conversation replays will be evaluated through reusable product invariants rather than a single required dialogue order.

Each scenario may declare:

```text
expected final NutritionBrief fields
facts that must remain stable after capture
fields that must not reappear as missing after capture
intentional field transitions
required and forbidden tools
expected final card counts
allowed reviewable-proposal delta
visible-text requirements and forbidden internal fragments
```

The harness records, per user turn:

```text
provider exchanges consumed by that turn
typed tool names requested
brief snapshot
cumulative card counts
card deltas
visible assistant message
```

The invariant report checks:

1. raw provider JSON and internal state names never reach visible text;
2. expected brief facts are present at the end;
3. captured facts survive later turns unless an explicit transition is declared;
4. known facts are not reintroduced as structured `missing_slots`;
5. `update_*` tools remain silent while explicit `read/share_*` tools own card rendering;
6. required tools are used and final apply tools are never provider-callable;
7. draft work does not mutate profile, weight history or final nutrition objects;
8. only explicitly expected `NutritionProposal` records may be created, and they remain pending review.

`assert_clean()` remains as a backward-compatible alias, but now executes the full invariant suite.

## Scenario coverage

Built-in scenarios cover:

- the original ficha-led flow without turn-index assertions;
- several facts delivered together and in free order;
- explicit change from daily plan/muscle gain to weekly program/fat loss;
- the anti-JSON visible boundary.

A database-backed replay test also invokes `create_validated_meal_proposal` through the real tool dispatcher. It verifies that a genuine pending-review `NutritionProposal` is created while no `Meal`, `DailyPlan`, `Program`, profile field or weight history is applied or mutated.

## Consequences

- Natural variations in question order no longer fail the suite by themselves.
- Tests still fail when state, tools, cards, persistence or visible-text boundaries regress.
- Multi-fact turns and changes of direction become first-class supported behavior.
- Replay diagnostics can explain which invariant failed rather than only showing an unexpected turn index.
- Exact copy remains testable only where the copy itself is a safety or boundary requirement.

## Validation contract

At minimum, CM22 must keep green:

```bash
python manage.py check
python manage.py test notas.tests.test_ai_assistant_conversation_replay -v 2
python manage.py test ai_assistant \
  notas.tests.test_ai_assistant_conversation_replay \
  notas.tests.test_ai_intake_ai_assistant_cards \
  notas.tests.test_ai_intake_llm_profile_cards \
  notas.tests.test_ai_profile_tools \
  notas.tests.test_ai_preference_tools \
  notas.tests.test_ai_proposal_preference_tools \
  notas.tests.test_ai_proposal_tools \
  notas.tests.test_ai_proposal_from_draft_tools -v 1
```

The management command must list scenario invariant outcomes in human-readable and JSON modes.

## Related decisions

- `0101-ai-assistant-conversation-debug-harness.md`
- `0102-ai-assistant-scripted-replay-scenarios.md`
- `0104-ai-assistant-draft-update-card-sharing-boundary.md`
- `0106-ai-assistant-adaptive-prompt-response-policy.md`
