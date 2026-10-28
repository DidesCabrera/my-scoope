# Target state for the My Scoope development area

Use this as the desired operating condition for simultaneous local work. It is a
repository convention, not a universal Git requirement.

## Control checkout

The original checkout at `/Users/felipedides/Developer/my-scoope` acts as the
control checkout:

- clean outside an explicitly recorded coordination change;
- parked on local `staging` when it is not performing a declared integration;
- local `staging` equal to the confirmed remote `staging` head before creating
  new work;
- not used for ordinary feature implementation;
- not the source of Metro for a feature under test.

This keeps one predictable place for auditing, creating worktrees, and reviewing
integration state. It does not make the checkout or `staging` authoritative over
GitHub.

## Active work

- Every active task has one declared managed worktree, branch, owner/chat, base
  commit, intended integration target, and lifecycle state.
- New ordinary application work begins from the confirmed remote `staging` head.
- Uncommitted changes belong to exactly one declared task.
- A branch checked out nowhere is not considered active without ownership
  evidence from its task or pull request.
- Worktree state and task state agree; missing or unregistered paths are treated
  as incidents to reconcile, not silently pruned.

## Metro and simulators

- Every running Metro/Expo process has a declared task, worktree, environment,
  port, PID, device/client, and start time.
- The client under test points to that declared port and environment.
- A task releases its Metro reservation when testing ends.
- Multiple Metro processes are allowed only when ports, clients, and ownership
  are explicit and non-conflicting.

## Integration and validation

- The validation tier follows the applicable `AGENTS.md` policy.
- The exact validated commit is the commit published and integrated.
- Remote publication and PR/merge state are verified from authoritative remote
  evidence rather than inferred from branch names.
- Post-merge evidence tests deployment or environment health instead of merely
  repeating the same code suite.

## Hygiene

- Local `staging` and `main` do not drift indefinitely from their confirmed
  remote heads.
- Every local feature branch is classified as active, published, integrated,
  archive-ready, blocked, or explicitly abandoned.
- Integrated inactive worktrees are archived recoverably after ignored files and
  active processes are checked.
- Local and remote branch deletion are separate, explicitly authorized actions.
- The normal audit has no unexplained high-severity findings and no unknown
  ownership for active work or Metro sessions.

## Readiness thresholds

The area is **healthy** when all control, ownership, Metro, and remote-freshness
conditions are met and no high-severity findings exist.

It is **degraded** when work can continue but one or more conditions need manual
attention, such as local branch drift, unclassified inactive branches, or remote
evidence temporarily unavailable.

It is **unsafe for parallel testing or cleanup** when Metro ownership is unclear,
a dirty worktree has no owner, a checkout is missing/unregistered, or deletion
preconditions are not established.
