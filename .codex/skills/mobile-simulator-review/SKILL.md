---
name: mobile-simulator-review
description: "Present an already implemented My Scoope mobile change in the iOS Simulator with the smallest possible action set. Use when Felipe asks to show, open, reload, or see a change. This workflow never implements, validates, integrates, deploys, or fabricates preview data."
---

# Mobile Simulator Review

Show an already implemented change in the iOS Simulator. This is a presentation
workflow, not an implementation, debugging, validation, or release workflow.
Communicate in Spanish unless Felipe requests another language.

## Hard boundary

A request such as “muéstrame el cambio”, “ábrelo en el simulador” or “refresca la
app” authorizes only simulator presentation.

Never do any of the following in this workflow:

- edit, add, delete, or reformat repository files;
- create preview routes, mock data, fixtures, redirects, or temporary UI;
- run tests, lint, type checks, CI scripts, builds, migrations, or seed commands;
- inspect broad source code, diffs, documentation, branch history, or architecture;
- start a backend, database, worker, deployment, integration, fetch, push, or PR;
- erase simulator data, sessions, credentials, or another chat's Metro process;
- substitute representative data for the actual requested behavior;
- repeat navigation experiments after one direct retry.

Do not turn missing validation into work. Report that it was not part of this
presentation request. Do not turn a missing backend or dataset into environment
setup. Report the missing dependency and stop.

## Fast path

Use the expected screen and route from the current conversation. Do not reread the
feature to rediscover information already present in the task.

Perform at most these actions:

1. Determine the current checkout root and run
   `scripts/inspect_preview_context.sh` once for the intended Metro port.
2. If Metro belongs to this checkout, reload the client. If it belongs to another
   checkout, leave it running and start Metro for this checkout on a free port.
3. Connect the simulator client to that port and open the existing route.
4. If the route does not open, retry once using the other existing direct method:
   app navigation or deep link. Do not change code to force navigation.
5. Capture the visible result.

For ordinary JavaScript, TypeScript, style, copy, and bundled asset changes, never
rebuild the native app. If the change actually requires a native rebuild, state
that clearly before running the existing repository build command; do not perform
any other preparation.

## Multiple chats

Each active worktree must use its own Metro port. A simulator can display only the
bundle to which its current development client is connected. Before presenting a
result, require that the Metro process directory equals the current worktree's
`mobile/` directory. Never capture another chat's bundle as evidence.

## Stop conditions

Stop immediately and report one concrete blocker when any of these is true:

- the existing route cannot be opened after one retry;
- the required API, authentication, or data is absent from the connected environment;
- only a native rebuild could expose the change and it has not yet completed;
- simulator control is unavailable;
- the requested change has not actually been implemented.

Do not solve the blocker within this workflow unless Felipe separately asks for
that work.

## Response

Return only:

- the screenshot or visible simulator result;
- one short line with the checkout path and Metro port; or
- one short sentence naming the blocker.

Do not include an audit, test report, implementation summary, or extended evidence
packet unless Felipe explicitly asks for one.
