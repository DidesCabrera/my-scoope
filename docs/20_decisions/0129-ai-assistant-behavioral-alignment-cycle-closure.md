# 0129 — AI Assistant Behavioral Alignment cycle closure

Status: accepted
Date: 2026-07-15
Scope: BA07 closure; BA00-BA07 and PT00-PT06 final regression evidence

## Decision

Close the AI Assistant Behavioral Alignment cycle BA00-BA07. The behavioral contract promoted in decision 0128 is now the current implementation baseline, and the required whole-project regression boundary has passed.

This closure does not introduce a new conversational script. It confirms the accepted product posture:

- guide the LLM with My Scoope purpose, current state, typed capabilities and boundaries;
- keep ambiguous references free from unjustified reads, writes and cards;
- progress sufficiently grounded tasks toward useful reviewable outcomes;
- avoid re-asking facts already available in the current turn, profile, drafts or visible cards;
- preserve provider-native `call_id` values exactly and validate post-tool continuations before remote I/O;
- treat `state_ack_only.v2` as a rare degraded fallback, not a healthy provider-authored turn.

## Accepted live evidence

```text
run_id: 735444ac6d9b4ffe8087a5ec6e3f3e23
provider/model: openai/gpt-5.4-mini-2026-03-17
automated status: passed
profile fixture: available weight_kg, height_cm; genuinely missing age_years, sex
behavior: known facts not re-asked; only genuine gaps named; ambiguous reference executed zero tools
session disposition: accepted for BA07 closure
```

## Whole-project boundary

The authoritative boundary is the repository script, not an unconfigured raw test command:

```bash
scripts/ci_django_checks.sh
```

Final result from the fresh `full` workspace:

```text
Django system checks: 0 issues
core.tests.regressions: 2 tests passed
full Django suite: 1,446 tests passed
full-suite duration: 235.386 seconds
```

The first authoritative run exposed 13 stale documentation-test paths left behind by the numbered `docs/` information architecture. Those tests still referenced:

```text
docs/current
docs/planning
docs/decisions
```

They were aligned to:

```text
docs/00_current
docs/10_active_cycles
docs/20_decisions
```

The focused documentation tests then passed 16/16, followed by the complete green boundary above.

## Clarification about onboarding redirects

A preliminary sandbox invocation ran `python manage.py test` directly with the production-default onboarding gate enabled. The resulting redirects were configuration-sensitive and did not represent the repository's CI contract, which explicitly sets `NUTRITION_ONBOARDING_GATE_ENABLED=false` for the broad historical suite.

The runtime onboarding middleware remains protected. Future whole-project closure checks must use `scripts/ci_django_checks.sh` or reproduce its explicit environment exactly.

## Consequences

- BA00-BA07 is completed.
- PT00-PT06 remains completed as the transport correction cycle supporting this baseline.
- `docs/00_current/` is the implementation source of truth.
- Future AI Assistant changes require a newly scoped cycle grounded in observed product evidence.
- New work should improve typed tools, object contracts, evaluations or product capabilities before adding global prompt complexity.
