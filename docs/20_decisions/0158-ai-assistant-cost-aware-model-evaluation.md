# 0158 · AI Assistant cost-aware model evaluation

Status: accepted and implemented

## Decision

My Scoope will run the production AI Assistant on the cheapest GPT-5.6-family
model that satisfies the assistant's hard behavioral gates and manual UX review.

The default production baseline is:

- Model: `gpt-5.6-luna`
- Reasoning effort: `low`
- Role: baseline

Escalation and benchmark roles are explicit:

- `gpt-5.6-terra` is the preferred escalation candidate when Luna fails hard
  checks, produces degraded turns, or does not pass qualitative UX review.
- `gpt-5.6-sol` is benchmark-only by default. It must not be executed during
  routine evaluation unless the operator passes an explicit benchmark flag or
  selects that candidate by code.

## Rationale

The assistant's tool graph is bounded and product-specific. It needs natural
conversation, correct tool use, grounded proposal creation and memory stability,
but it does not require the most expensive model on every turn by default.

OpenAI's current GPT-5.6 guidance positions Luna for cost-sensitive/high-volume
workloads, Terra for balancing intelligence and cost, and Sol for frontier
complex work. Official pricing at the time of this decision is:

- `gpt-5.6-luna`: $0.20 input, $0.02 cached input, $1.20 output per 1M tokens.
- `gpt-5.6-terra`: $2.00 input, $0.20 cached input, $12.00 output per 1M tokens.
- `gpt-5.6-sol`: $5.00 input, $0.50 cached input, $30.00 output per 1M tokens.

## Implementation

`AI_ASSISTANT_OPENAI_MODEL` now defaults to `gpt-5.6-luna` and
`AI_ASSISTANT_OPENAI_REASONING_EFFORT` defaults to `low`.

`AI_ASSISTANT_MODEL_EVALUATION_CANDIDATES` defines the default candidate set:

- `luna_low` baseline
- `terra_low` escalation
- `terra_medium` quality check
- `sol_medium` benchmark

The command below runs the same real-provider validation scenarios across the
non-benchmark candidates and emits a JSON report with quality and cost metrics:

```bash
.venv/bin/python manage.py evaluate_ai_assistant_models \
  --live \
  --user-email staging-user@example.com \
  --fail-on-no-accepted-candidate \
  --json
```

Use `--include-benchmarks` to include `sol_medium` deliberately.

## Quality contract

The selected non-benchmark model must pass the hard automated checks from the
outcome-first validation suite. The report also records:

- scenario pass rate;
- hard-check pass rate;
- degraded/local-ack turns;
- provider follow-up failures;
- native tool calls;
- input/output/total tokens;
- estimated cost in USD.

Passing the automated report is not enough for release. The accepted model still
requires manual UX review of the generated transcripts.
