# 0157 · AI Assistant outcome-first runtime

Status: accepted and implemented

## Decision

My Scoope has one active assistant runtime: a real OpenAI model operating through
the Responses API with native function tools. The assistant owns the
conversation, uses persisted context as memory, and continues a turn until it
has either produced the requested outcome or identified one genuinely blocking
field.

The runtime must not route a customer to the deterministic interviewer, a
preview engine, a percentage rollout, or a fake provider. Legacy mode names are
accepted only as deployment compatibility input and normalize immediately to
`llm`; they do not select alternate behavior.

This decision supersedes the active runtime and rollout parts of decisions
0030, 0042, 0108, and 0109. Those documents remain historical records.

## Product contract

- The visible response is natural text, not a JSON envelope.
- Conversation history is forwarded as alternating user and assistant messages.
- Known profile and conversation facts are never requested again.
- Optional proposal preferences use explicit defaults instead of blocking.
- When the requested proposal is ready, the model must call the proposal tool
  in the same turn. Saying that it is ready is not a successful outcome.
- Proposal creation produces a reviewable card; it does not silently publish a
  final plan.
- Tool calls use provider-native function transport and validated local
  execution. The model does not manufacture tool state.
- Provider failure returns a clear, non-destructive error. It never invokes the
  old interviewer for the same message.
- The UI renders a deliberately small, escaped Markdown subset so useful
  formatting is readable without allowing raw HTML.

## Runtime defaults

- Provider: `openai`
- Model: `gpt-5.6-luna`
- Reasoning effort: `low`
- History: 20 messages
- Maximum visible output: 2,400 tokens
- Tool loop: 4 iterations
- Input budget: 20,000 estimated tokens
- Reviewable proposal tools: enabled

Decision 0158 adds the cost-aware evaluation policy: Luna is the default
baseline, Terra is the preferred escalation candidate, and Sol is benchmark-only
unless a measured workflow justifies its production cost.

## Release gates

Deployment checks fail closed when the OpenAI provider, API key, proposal tools,
credit enforcement, pricing, or technical limits are missing. There is no
engine mode that can bypass these checks.

Offline tests cover history, exact blocker calculation, natural response
parsing, native tool execution, same-turn proposal creation, state enrichment,
safe UI formatting, credit and usage accounting, and the customer-facing chat
boundary.

The live release gate runs the same unified engine and requires:

```bash
.venv/bin/python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email staging-user@example.com \
  --fail-on-hard-regression \
  --json
```

The command consumes real provider usage. Its automated checks must pass, then
the transcript receives the included human UX review.

## Removal

The percentage/staff/allowlist rollout implementation, settings, environment
contract, and tests are removed. The deterministic engine is not reachable from
the product selector; it remains only where explicitly injected by isolated
legacy parsing tests until those fixtures are replaced.
