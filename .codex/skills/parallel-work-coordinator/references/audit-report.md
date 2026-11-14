# Audit report contract

The audit must make evidence easy to verify and uncertainty hard to overlook.

## Required sections

1. **Scope and freshness** — repository, timestamp, current checkout, remote
   `staging`/`main` heads, corresponding cached refs, equality status, and an
   explicit statement that no fetch occurred.
2. **Branches and checkouts** — a branch-centered table with one branch per
   row. Include its checkout path (or none), HEAD, cleanliness, upstream, local
   ancestry against `staging` and `main` when those refs exist, divergence,
   and missing-path errors. Show detached worktrees separately; they have no
   branch to occupy a row.
3. **Metro/Expo processes** — PID, command summary, working directory when
   discoverable, and listening ports when discoverable.
4. **Findings** — observations with severity and evidence.
5. **Limits and next steps** — what cannot be concluded from local read-only
   evidence and which additional read-only evidence would resolve it.
6. **Target-state gap** — when requested, compare evidence with
   `target-state.md`; do not convert recommendations into authorized mutations.

## Current-state dashboard

When the user asks for the state of the development area, work area, branches,
checkouts, or requests a dashboard in an established repository-coordination
context, present an operational snapshot rather than a historical activity log.
Build it from a fresh audit, including the direct read-only remote check whenever
available.

Use this default order:

1. **Indicators** — counts for active checkouts, dirty checkouts, Metro/Expo
   processes, remote task branches, unresolved preserved work, and high-risk
   coordination findings.
2. **Branches** — one table row for each independent branch, including
   `staging`, `main`, active task branches, and preserved branches without a
   checkout. Useful columns are branch, checkout (or none), short local and
   remote HEADs, remote relationship, cleanliness, integration status, and next
   action. Keep local and remote information for the same branch in one row.
   Never combine multiple branches into a row such as "other branches".
3. **Detached checkouts** — list separately with path, short HEAD, cleanliness,
   and relationship to `staging` or `main`. They are not branches.
4. **Metro/Expo processes and findings** — include when relevant to the user's
   requested scope and explain any material coordination risk.

Use compact traffic-light markers consistently:

- 🟢 healthy, current, clean, or no action required;
- 🟡 preserved uncertainty or a human decision required;
- 🔴 an active correctness or data-loss risk;
- ⚪ unknown or unavailable evidence.

Keep completed cleanup, deleted branches, archived worktrees, and CI history out
of the default dashboard. Include them only when the user asks for history or
when a recent action materially explains the current state. A branch without an
active worktree must not be presented as an active checkout.

Treat "production area" as this repository-work dashboard only when the
conversation clearly refers to branches, checkouts, worktrees, or Metro. If it
instead refers to the deployed production environment, route to deployment and
service-health evidence rather than this dashboard.

## Severity

- **Critical:** evidence of likely data loss or a destructive action already in
  progress. Read-only observation normally should not produce this severity.
- **High:** state confusion can cause work or testing against the wrong checkout,
  such as multiple Metro processes or a dirty detached worktree.
- **Medium:** integration or ownership needs attention, such as substantial
  divergence, missing upstream, or an unattributed Metro process.
- **Low:** hygiene or clarity improvement with no immediate correctness risk.
- **Info:** neutral inventory.

## Language rules

Use "candidate for review" rather than "safe to delete" unless all cleanup
preconditions have been independently established. Say "locally reachable from"
rather than "merged" when the evidence is Git ancestry only. Say "unknown" when
the process working directory, intended target, remote freshness, or ownership is
not established.
