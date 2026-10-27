---
name: mobile-simulator-review
description: "Show an implemented My Scoope mobile change in the iOS Simulator using Fast Refresh when possible. Use when Felipe asks to show, open, reload, or see a change, especially when the simulator may be connected to the wrong branch, Metro port, or API environment. This workflow prepares the presentation runtime; it does not implement or integrate code."
---

# Mobile Simulator Review

Present the change that already exists in the task's mobile checkout. Optimize for
the shortest reliable path to the visible screen. Communicate in Spanish unless
Felipe requests another language.

## Runtime model

Keep these two processes independent:

- **Metro owns the mobile source.** Fast Refresh only observes the checkout from
  which Metro was started. A Metro process started in a `staging` checkout cannot
  show uncommitted changes from another branch or worktree.
- **The API owns the data.** The mobile feature checkout may use the deployed
  staging API or a Django server running from a separate staging checkout, as long
  as their API contracts are compatible.

The default presentation topology is:

```text
feature worktree/mobile -> its own Metro port -> iOS Simulator
                                      |
                                      +-> deployed staging API
```

Always point the simulator presentation at the deployed Render staging API through
`npm run start:staging`. Do not start or select a local Django backend merely
because one is available. Use a local backend only when Felipe explicitly requests
that environment in the current task; in that exceptional mode, start Metro from
the feature checkout with the local profile so it points to
`http://127.0.0.1:8000`.

A simulator displays one development bundle at a time. Two chats may keep separate
Metro processes running, but showing another chat requires reconnecting the client
to that chat's port.

## What the request authorizes

“Muéstrame el cambio” authorizes the reversible presentation work needed to:

- inspect the current checkout and active Metro ports;
- reuse or start Metro from the checkout that owns the change;
- boot or foreground the existing iOS Simulator and development client;
- connect that client to the selected Metro port;
- reload, follow an existing deep link or navigate through the existing app;
- capture the visible result.

It does not authorize editing product code, inventing preview data, running test or
CI suites, integrating branches, pushing, deploying, erasing simulator state, or
terminating another chat's processes.

## Fast path

1. Identify the checkout that contains the requested change and the expected
   screen from the current conversation. Do not inspect broad history or rediscover
   the feature.
2. From that checkout, run `scripts/inspect_preview_context.sh`. Use its matching
   Metro port when one exists; otherwise use the reported free port.
3. Run `npm run start:staging -- --port <port>` from that checkout's `mobile/`
   directory. This points the app at `https://myscoope-staging.onrender.com`.
   Substitute a local backend and `npm run start:local` only when Felipe explicitly
   requests that environment in the current task.
4. Connect the existing development client directly to that Metro port with:

   ```bash
   xcrun simctl openurl booted "exp+my-scoope://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A<port>"
   ```

   Do not rebuild it for JavaScript, TypeScript, styles, copy, or bundled assets.
5. Open the known route. Retry once after a reload if Fast Refresh left stale
   state. Then capture the result and stop.

If the matching Metro is already running, do not restart the backend, reinstall
dependencies, rebuild iOS, or launch another Metro.

## When Fast Refresh is insufficient

Restart Metro when environment variables or Metro-time configuration changed.
Rebuild the development client only when the change affects native dependencies,
Expo plugins, entitlements, native iOS code, or another native build input. A
request to show a change does not authorize that rebuild: state the concrete reason
and ask Felipe before starting the repository's existing build command.

Fast Refresh cannot make a feature work against an incompatible API. If the mobile
change requires backend code absent from the selected API, name that mismatch and
switch to the compatible already implemented backend only when it is available.
Do not implement missing backend work in this workflow.

## Stop conditions

Stop with one concrete blocker when the requested change is absent, the required
API or authentication is unavailable, the route fails after one reload and one
direct navigation attempt, a native rebuild is required but not authorized, or
simulator control is unavailable.

## Response

Show the screenshot or visible simulator result and report only the mobile
checkout, Metro port, and API mode. If blocked, give one short sentence naming the
blocker and the smallest next action.
