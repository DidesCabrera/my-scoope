---
name: parallel-work-coordinator
description: Audit parallel repository work across remote branches, worktrees, local branches, and Metro/Expo; present current-state operational dashboards; maintain a local ownership registry and Metro leases. Use when coordinating simultaneous Codex tasks, diagnosing checkout confusion, assessing development-area health, reporting the state of the work area, reviewing integration readiness, or planning safe cleanup. Audits are read-only; registry writes require an explicit coordination request and never mutate Git or processes.
---

# Parallel Work Coordinator

Establish a trustworthy snapshot before recommending any lifecycle action.

## Audit workflow

1. Run `scripts/audit_parallel_work.py` from any path inside the repository. Pass
   `--repo <path>` only when the intended repository is not the current one.
2. By default the script queries `origin` with `git ls-remote` for `staging` and
   `main`. This reads remote heads without updating local refs. If the query is
   unavailable, report remote freshness as unknown; do not silently fall back to
   treating cached refs as current.
3. Explain material risks first: dirty worktrees, detached worktrees, missing
   worktree paths, large divergence, branches checked out elsewhere, and Metro
   processes whose checkout does not match the work being reviewed.
4. Separate facts from recommendations. A branch that has no upstream, is old,
   or is behind its comparison ref is not thereby safe to delete.
5. For lifecycle classification and cleanup prerequisites, read
   [references/lifecycle-policy.md](references/lifecycle-policy.md).
6. For the report contract and severity meanings, read
   [references/audit-report.md](references/audit-report.md).
   When the user asks for the current state of the development area, work area,
   branches, checkouts, or an equivalent dashboard in an established repository
   coordination context, use the current-state dashboard defined there by
   default.
7. When assessing health or proposing improvements, read
   [references/target-state.md](references/target-state.md) and express the plan
   as gaps from current evidence to the target state.
8. The audit reads the shared operational registry when it exists. For registry
   and Metro-lease operations, read
   [references/operational-registry.md](references/operational-registry.md) and
   use `scripts/manage_parallel_work.py` rather than editing JSON manually.

## Read-only boundary

Do not mutate Git, GitHub, Codex worktrees, processes, ports, simulators, or
Metro sessions while auditing. In particular, do not run
`fetch`, `pull`, `checkout`, `switch`, `merge`, `rebase`, `reset`, `clean`,
`worktree add/remove/prune`, branch deletion, process termination, or package
commands that may install dependencies or start services.

Registry commands may write only the shared coordination state under the Git
common directory, and only when the user requests registration or lease changes.

If the user asks to repair or clean up after the audit, present an explicit plan
and obtain the authorization required for that separate mutation. Do not extend
this skill's audit script into an apply mode.

## Evidence limits

- Branch divergence uses local objects. Remote-head equality is checked directly,
  but divergence against a newer remote commit remains unknown until that commit
  exists locally.
- "Merged locally" means commit ancestry against an available local comparison
  ref; it does not prove that a pull request was merged.
- Metro attribution is best effort. Report an unknown working directory instead
  of guessing.
- Never infer ownership from a branch name alone.
