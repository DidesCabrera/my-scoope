# Parallel work lifecycle policy

Use this policy when interpreting an audit or proposing a later lifecycle action.

## States

| State | Minimum evidence |
| --- | --- |
| Planned | Work has an objective and intended base but no checkout yet. |
| Active | A task owns a checkout or branch and implementation is ongoing. |
| Validation | Implementation is closed for the current refinement stage and the applicable validation tier is running or recorded. |
| Published | The exact validated commit is available remotely. |
| Integrated | The exact work commit is reachable from its intended integration target, or the authoritative PR provider confirms merge. |
| Archive-ready | Integrated, worktree clean, no active process attributed to it, and relevant ignored files have been reviewed. |
| Cleaned | Checkout/worktree and eligible local branch were removed through an authorized, recoverable workflow. |
| Blocked | Progress requires a user decision, external state change, or unavailable prerequisite. |
| Abandoned | The owner explicitly chose not to continue; this alone does not authorize deletion. |

## Invariants

- One active task should have one declared checkout and branch.
- A branch checked out in any worktree is active infrastructure until proven
  otherwise.
- A running Metro/Expo process belongs to the checkout from which it was started,
  not to whichever checkout is currently visible to the user.
- Dirty worktrees, untracked files, ignored operational artifacts, detached HEADs,
  missing remote evidence, and uncertain ownership block automatic cleanup.
- Being behind `staging` or `main` is a synchronization concern, not evidence that
  work is obsolete.
- "No upstream" means publication state is unknown; it does not mean local-only
  work is disposable.
- Cleanup requires a fresh audit immediately before the authorized action.

## Integration targets

Do not guess the intended target solely from ancestry. Prefer, in order:

1. an explicitly recorded task or PR target;
2. the user's current instruction;
3. repository release policy;
4. a clearly configured upstream;
5. otherwise, report the target as unknown.

For this repository, respect the validation and integration policy in the
applicable `AGENTS.md`. The audit does not run validation suites.

## Cleanup planning

A later cleanup plan must list each proposed action independently: archive or
remove worktree, delete local branch, delete remote branch, stop a process, or
remove auxiliary files. Authorization for one action does not imply the others.

Prefer recoverable Codex worktree archival when the worktree is managed by Codex.
Never use force deletion as a default or as a shortcut around missing evidence.
