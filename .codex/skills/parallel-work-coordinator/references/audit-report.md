# Audit report contract

The audit must make evidence easy to verify and uncertainty hard to overlook.

## Required sections

1. **Scope and freshness** — repository, timestamp, current checkout, remote
   `staging`/`main` heads, corresponding cached refs, equality status, and an
   explicit statement that no fetch occurred.
2. **Worktrees** — path, branch or detached state, HEAD, cleanliness, upstream,
   divergence, and missing-path errors.
3. **Branches** — local branch, upstream, checkout ownership, local ancestry
   against `staging` and `main` when those refs exist, and divergence.
4. **Metro/Expo processes** — PID, command summary, working directory when
   discoverable, and listening ports when discoverable.
5. **Findings** — observations with severity and evidence.
6. **Limits and next steps** — what cannot be concluded from local read-only
   evidence and which additional read-only evidence would resolve it.
7. **Target-state gap** — when requested, compare evidence with
   `target-state.md`; do not convert recommendations into authorized mutations.

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
