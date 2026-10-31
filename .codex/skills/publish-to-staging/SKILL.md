---
name: publish-to-staging
description: Publish the current My Scoope task to the latest origin/staging after proportionate validation and confirm the exact remote CI result. Use when Felipe says "publica este trabajo en staging", "integra este trabajo en staging", or an equivalent short instruction. Do not use for main, production deployment, worktree cleanup, branch deletion, or unrelated housekeeping.
---

# Publish to Staging

Treat the short instruction **“publica este trabajo en staging”** as authorization
for the bounded workflow below. It does not authorize production publication or
cleanup outside the current task.

## Workflow

1. Read `AGENTS.md` and the repository testing/CI policy. Identify the current
   task checkout, branch, intended files, and whether visual or functional user
   approval is still pending. Do not begin integration while active refinement
   still requires approval.
2. Fetch `origin` with pruning. Verify the current `origin/staging` and
   `origin/main` relationship. If production history is absent from staging,
   stop and report the reconciliation requirement instead of publishing over it.
3. Inspect tracked, untracked, and relevant ignored files. Never include unrelated
   work merely because it is present in the checkout.
4. Run the validation tier that owns the changed risk, following the repository's
   efficient validation policy. State the tier and expected cost. Commit only the
   intended validated content.
5. Fetch again immediately before publication. If `origin/staging` advanced,
   incorporate it deliberately and rerun only the evidence invalidated by that
   change. The exact commit to publish must be the exact content validated.
6. Push that commit to `origin/staging`, then wait for and report the required
   GitHub Actions result for the exact remote commit. A failed or missing required
   check blocks treating the staging integration as successful.
7. Stop when the exact published commit and its required CI result are known.
   Updating a local control checkout, archiving a worktree, and deleting an
   integrated branch are separate housekeeping outcomes and require a separate
   user request.

## Boundaries

This instruction does not authorize:

- pushing or merging to `main`;
- deploying or verifying production;
- updating another checkout, including a local `staging` control checkout;
- archiving or deleting the current worktree or local branch;
- deleting remote branches;
- force-updating shared refs;
- deleting a dirty, unverified, or non-integrated branch;
- stopping Metro or cleaning another task's files or checkout.

Stop with a concrete blocker when the task cannot be published without one of
those actions or without a user decision.

## Report

Return the published commit, remote target, validation tier and outcome, and exact
CI run result. State that the task checkout and branch remain available unless the
user separately requested their closure.
