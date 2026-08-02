# AI Assistant outcome-first runbook

## Required deployment configuration

```text
AI_ASSISTANT_CHAT_ENGINE_MODE=llm
AI_ASSISTANT_LLM_PROVIDER=openai
AI_ASSISTANT_OPENAI_API_KEY=<deployment secret>
AI_ASSISTANT_OPENAI_MODEL=gpt-5.6-luna
AI_ASSISTANT_OPENAI_REASONING_EFFORT=low
AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=true
AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS=true
AI_ASSISTANT_CREDITS_ENABLED=true
```

Keep the limits in `.env.example` unless a measured evaluation justifies a
change. Never commit the API key. `gpt-5.6-terra` is the preferred escalation
candidate when Luna fails hard quality checks or manual UX review. `gpt-5.6-sol`
is a benchmark-only candidate unless a measured customer workflow proves that
the extra cost is justified.

## Pre-deployment gate

```bash
.venv/bin/python manage.py check --deploy
.venv/bin/python manage.py test ai_assistant.tests
.venv/bin/python manage.py test \
  notas.tests.test_ai_assistant_chat_engine \
  notas.tests.test_ai_assistant_real_provider_validation \
  notas.tests.test_ai_intake_runtime_boundary \
  notas.tests.test_ai_intake_subject_context \
  notas.tests.test_ai_intake_tool_led_regressions
```

Any `ai_assistant.E00*` result blocks deployment.

## Real-provider validation

List the scenarios without spending provider usage:

```bash
.venv/bin/python manage.py validate_ai_assistant_real_provider --list-scenarios
```

Run them with one existing staging user:

```bash
.venv/bin/python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email staging-user@example.com \
  --fail-on-hard-regression \
  --json
```

The automated gate checks provider health, natural visible text, tool
transport, memory stability, no repeated known facts, proposal/card pacing,
usage recording, and post-tool response health. Complete the qualitative
questions printed in the report before release.

## Model quality/cost evaluation

List the configured candidates without spending provider usage:

```bash
.venv/bin/python manage.py evaluate_ai_assistant_models --list-candidates
```

Run the default comparison. This evaluates non-benchmark candidates only, so it
starts with Luna and Terra without spending Sol usage by accident:

```bash
.venv/bin/python manage.py evaluate_ai_assistant_models \
  --live \
  --user-email staging-user@example.com \
  --fail-on-no-accepted-candidate \
  --json
```

Use `--include-benchmarks` only when you deliberately want a Sol comparison.
Use `--scenario` to run a smaller diagnostic slice while iterating. The report
includes hard-check pass rates, degraded turns, native tool calls, token totals,
estimated cost, and an automatic recommendation. Any accepted model still
requires manual UX review before release.

## Operational failure behavior

If OpenAI is unavailable, the user receives a bounded message stating that the
request was not completed and that no change was made. Investigate the usage
event and provider diagnostics. Do not restore the deterministic interviewer or
add a silent fake-provider fallback.
