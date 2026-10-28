# Operational registry

The registry stores declared intent and ownership. Git, GitHub, Codex worktrees,
and operating-system processes remain authoritative for observed facts.

## Location

`scripts/manage_parallel_work.py` resolves the repository's shared Git common
directory and stores state at:

```text
<git-common-dir>/codex/parallel-work-state.json
```

This makes one machine-local registry visible from every linked worktree without
adding runtime state to commits.

## Work record

Each record has:

- stable work ID;
- owning chat or human label;
- branch and absolute worktree path;
- exact base commit and intended integration target;
- lifecycle state from `lifecycle-policy.md`;
- creation and update timestamps.

Registration never creates a branch or worktree. It records an already observed
or explicitly planned relationship.

## Metro lease

A lease records work ID, port, environment, optional PID and device, and claim
time. Claiming a lease never starts Metro. Releasing a lease never stops a
process. The audit compares leases with observed listeners and reports drift.

One port may have only one lease. Replacing a lease owned by another work item
requires `--force` and explicit user authorization.

## Commands

```text
manage_parallel_work.py init
manage_parallel_work.py show
manage_parallel_work.py register-work --id ID --owner OWNER --branch BRANCH \
  [--worktree PATH] --base COMMIT --target TARGET --status STATE [--note TEXT]
manage_parallel_work.py set-status --id ID --status STATE
manage_parallel_work.py claim-metro --work-id ID --port PORT \
  --environment NAME [--pid PID] [--device NAME]
manage_parallel_work.py release-metro --port PORT --work-id ID
```

Use `--repo` when the current directory is not inside the intended repository.
