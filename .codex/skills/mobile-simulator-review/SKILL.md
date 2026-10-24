---
name: mobile-simulator-review
description: "Show the current My Scoope mobile change in an iOS Simulator from the intended checkout, Metro server, native build, and backend environment. Use when Felipe asks to show, open, refresh, or verify a mobile change visually, especially when a stale bundle or build may hide the latest code. Do not use for release builds or general feature implementation."
---

# Mobile Simulator Review

Make the intended mobile change visibly reviewable in the iOS Simulator and prove
which source and environment produced what Felipe sees. This is a shared workflow,
not a role: any role working on a mobile change may use it. Communicate in Spanish
unless the user requests another language.

Treat brief requests such as “muéstrame este cambio en el simulador”, “abre la
versión actual” or “refresca la app” as instructions to complete this workflow.
Infer the expected screen and behavior from the current task and diff when possible.

## Establish the preview identity

Read `AGENTS.md`, `mobile/README.md`, and only the current feature source needed to
understand the expected screen. Do not use the human Knowledge Center as product
evidence.

Before opening the app, establish:

- the absolute checkout path, current branch, commit, and relevant working changes;
- the active Metro process and the directory it serves;
- the intended development profile and API environment;
- the simulator, installed development client, route, and state needed for review.

Run `scripts/inspect_preview_context.sh` from this skill to compare the current
checkout with the Metro listener. Do not assume that an open simulator or a running
Metro belongs to the current chat or worktree. If another checkout owns the port,
do not terminate it blindly; connect the intended development client to a server
started from the correct checkout on an available port, or restart it only after
its ownership is clear.

For the normal staging-backed simulator loop, use the guarded repository commands
from `mobile/`:

```bash
npm run start:staging
npm run ios:staging
```

Use `start:staging` for the normal Metro loop. Use `ios:staging` only when the
installed native development build must change. Run `npm run verify:environments`
when environment identity is uncertain.

## Choose the smallest refresh that can show the change

- For JavaScript, TypeScript, styling, copy, or bundled asset changes, serve the
  intended checkout through Metro and use Fast Refresh or an explicit reload.
- For native dependencies, Expo plugins, entitlements, app configuration, generated
  iOS files, or native modules, rebuild and install the staging simulator client
  before reloading JavaScript.
- For backend, schema, authorization, or server-data changes, verify that the API
  environment used by the simulator contains the change. A current mobile bundle
  cannot expose backend code that exists only in a local checkout. Prefer an
  already-authorized local environment when suitable; obtain explicit authority
  before deploying or changing an external environment.
- For session or cached application state, reproduce with the least destructive
  state change. Do not erase simulator data, credentials, or user state merely as a
  generic refresh step.

If the change crosses more than one boundary, satisfy each required layer. Never
claim that a Metro reload proves a native rebuild, backend deployment, migration,
or installed release.

## Validate during visual iteration

Run the smallest focused check before presenting the screen. For a visual mobile
change, use `scripts/ci_mobile_visual_check.sh` from the repository root and pass
only the directly related test when one exists. Do not run the global typecheck,
the full mobile test set, or `ci_mobile_iteration.sh` for each visual adjustment.

Then navigate to the exact screen and state that demonstrates the requested
behavior. Capture or present visual evidence when the available simulator tooling
supports it. If the screen cannot be shown, identify the exact missing layer—source,
Metro, native build, API environment, test data, authentication, or simulator
control—instead of presenting an older version as current.

## Report the review state

Return a compact evidence packet containing:

- checkout, branch, commit, and whether relevant changes are uncommitted;
- Metro source directory and port;
- simulator profile and API environment;
- refresh or rebuild action performed;
- focused validation performed and its limits;
- screen or behavior shown, plus any layer still not verified.
