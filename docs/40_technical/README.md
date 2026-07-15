# 40 Technical

Status: current
Last updated: 2026-07-08

This folder contains operational technical documentation for My Scoope.

Use it for policies and evidence that guide how the project is tested, exported, stabilized and operated, without mixing those concerns into product/architecture source-of-truth documents.

## Structure

```text
docs/40_technical/
  operations/
  qa/
```

## `operations/`

Operational policies and workflows, including:

- docs information architecture;
- export modes for ChatGPT/AI context;
- testing and CI policy.

## `qa/`

QA closures, staging stabilization notes and testing hygiene guidance.

## Authority

These documents are high authority for technical workflow. If they conflict with `docs/00_current/`, prefer:

- `docs/00_current/` for product and architecture behavior;
- `docs/40_technical/` for CI, QA, exports, testing workflow and operational validation.
