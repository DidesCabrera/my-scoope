---
name: fresh-task-checkout
description: "Prepare a new My Scoope engineering task from a freshly fetched authoritative remote base in an isolated checkout. Use when Felipe starts coding work, asks to begin from current code, or an existing branch or worktree may be stale. Do not use to merge, push, reset, delete, or discard existing work."
---

# Fresh Task Checkout

Start new engineering work from a proven current base without altering another
task's files. This is a shared workflow available to every technical role.
Communicate in Spanish unless the user requests another language.

Treat brief requests such as “empieza desde el código actualizado”, “prepara esta
tarea” or “parte del staging actual” as instructions to complete this workflow.

## Protect existing work

Read `AGENTS.md` and
`docs/40_technical/operations/testing_and_ci_policy.md`. Inspect `git status`,
branch tracking, and `git worktree list` before selecting a checkout.

Never update a dirty or unrelated checkout in place merely because it is already
open. Do not use `reset`, discard changes, switch its branch, or pull/rebase it as a
shortcut. New work should receive an isolated worktree unless Felipe explicitly
chooses an existing clean checkout whose identity has been verified.

## Resolve the authoritative base

1. Run `git fetch origin --prune`. A stale local remote-tracking ref is not proof of
   the current remote state. If fetching fails, report that freshness is unverified
   and do not describe the checkout as current.
2. Use `origin/staging` for ordinary feature, fix, refactor, documentation, and
   integration work. A local branch named `staging` is not the base authority.
3. Use `origin/main` only for work explicitly scoped to the production line, such
   as a production audit or authorized hotfix, or when Felipe names it directly.
4. Honor an explicitly named PR, commit, or remote branch when the task truly
   depends on it; record the exact resolved commit.
5. Run `scripts/inspect_task_base.sh` from this skill after fetching. If
   `origin/main` contains commits absent from `origin/staging`, stop ordinary task
   preparation and report that the integration base requires reconciliation. Do
   not silently merge the branches.

The fact that `origin/staging` is ahead of `origin/main` is normal during
integration. The dangerous state is production history missing from staging.

## Create the task boundary

Create a uniquely named `codex/<task>` branch and isolated worktree at the exact
resolved base commit. Prefer the Codex managed-worktree capability when available,
passing `origin/staging` or the explicitly selected ref rather than accepting an
implicit default branch.

Before editing, verify and record:

- absolute worktree path and branch;
- selected remote ref and its full commit SHA;
- successful fetch in this preparation run;
- clean initial worktree;
- zero commits between the new `HEAD` and the selected base;
- `origin/main` versus `origin/staging` divergence;
- whether the remote base's CI status was checked, green, failing, or unavailable.

Dependency installation or project setup may create ignored files, but it must not
change the recorded source base. Avoid broad setup until the task requires it.

## Recheck before integration

When the task later reaches its integration boundary, fetch again and compare its
recorded base with the new `origin/staging`. If integration advanced, incorporate
the current base deliberately and rerun only the validation invalidated by that
change. Do not rely on the branch name or the commit message as evidence that the
task still includes current staging.

This checkpoint does not authorize a push, merge, pull request, deployment, or
destructive cleanup. Those actions remain controlled by the task request and the
repository policy.

## Report

Return a compact start packet with the worktree, task branch, selected base ref,
base SHA, fetch result, cleanliness, staging/main divergence, CI evidence, and any
condition that prevents the new checkout from being called current.
