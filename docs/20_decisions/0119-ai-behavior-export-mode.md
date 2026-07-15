# 0119 — `ai_behavior` Export Mode

Status: accepted
Date: 2026-07-14
Scope: `scripts/export_for_chatgpt.sh`, AI collaboration context and behavioral alignment work

## Context

The `full` export is appropriate for whole-project regressions but is unnecessarily heavy for repeated work on conversational behavior. The existing `aiassistant` mode includes broad provider, credits, proposals, solver and MCP concerns, but does not explicitly prioritize the combined runtime/UI/test surface needed for behavioral alignment.

BA02-BA06 will repeatedly inspect:

- provider instructions and context;
- tool names, descriptions, schemas and selection;
- chat runtime and temporary state;
- cards and visible responses;
- fake-provider replays and real-provider validation;
- focused UI templates and current decisions.

Using `full` for every iteration adds noise and increases the chance that historical or unrelated product code competes for attention.

## Decision

Add a focused export mode:

```bash
./scripts/export_for_chatgpt.sh ai_behavior
```

The mode includes:

- the complete `ai_assistant` app;
- conversational intake and AI tool runtime from `notas`;
- relevant models, domain/application dependencies and migrations;
- chat templates, cards and focused frontend files;
- behavior/tool/replay/live-validation tests and commands;
- current AI documentation, active BA cycle and related decisions;
- minimal Account, Core, Food Catalog, Solver and MCP contracts needed to understand capabilities.

The mode excludes broad dashboards, external datasets, media, generated assets, local databases, environments and unrelated product UI.

The script also removes duplicated mode declarations that existed after ZIP generation. Each mode now has one canonical definition and one final summary branch.

## Usage boundary

Use `ai_behavior` for:

- domain anchoring;
- tool governance and capability explanations;
- ambiguous-intent restraint;
- conversational initiative;
- response quality;
- cards, replays and real-provider UX validation.

Use `aiassistant` when the task is broader AI infrastructure, credits, proposal execution, provider diagnostics or MCP integration.

Use `full` when the change crosses many apps, changes settings/migrations, causes import failures or requires broad regression evidence.

## Consequences

- BA iterations use a smaller, behavior-oriented working artifact.
- The export retains tests and the runtime contracts needed for safe patches.
- The mode is documented as a stable collaboration boundary rather than a one-off file filter.
