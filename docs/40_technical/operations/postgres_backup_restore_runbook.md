# PostgreSQL backup and restore runbook

Status: current
Date: 2026-08-03

## Targets

- RPO: at most 24 hours for a logical-backup incident; use point-in-time recovery
  for a more recent recovery point when available.
- RTO: four hours from incident declaration to a validated replacement database.
- Retention: Render PITR according to the paid workspace plan, plus a weekly
  logical export retained outside the Render account for 90 days.
- Drill: restore into an isolated database every month and before a major schema
  migration.

Render continuously backs up paid PostgreSQL instances and creates a new isolated
database for point-in-time recovery. Free instances do not provide this recovery
capability. Official procedure:
https://render.com/docs/postgresql-backups

## Backup checklist

1. Confirm the production database is on a paid plan and note the visible PITR
   window in Render's Recovery page.
2. Create a logical export from the Recovery page every week and copy it to the
   approved off-platform encrypted store.
3. Record timestamp, PostgreSQL major version, schema migration head, file size,
   checksum and operator in the operations log.
4. Never store a database URL, dump or customer data in Git.
5. Before a risky migration, create an on-demand export and verify it appears in
   the Recovery page.

## Preferred incident recovery: PITR

1. Stop or disable writers if corruption is still in progress.
2. In the Recovery page, restore the source database to a new database at the
   selected timestamp.
3. Leave the original database untouched.
4. Point a temporary validation service at the recovery database.
5. Run migrations only if the recovered schema is older than the application
   revision used for validation.
6. Validate row counts for users, account subscriptions, credit wallets/ledgers,
   billing records, nutrition objects and AI usage events.
7. Run the production smoke checklist against the validation service.
8. Update `DATABASE_URL` through the managed service reference and redeploy web,
   worker and cron together.
9. Monitor errors and write paths before retiring the original database.

## Logical export recovery

Use this only with an empty target database. Render's documented restore flow uses
the PostgreSQL client version matching the source major version and `pg_restore`
for archive exports. Do not add destructive restore commands to project scripts.

1. Provision an empty isolated PostgreSQL database.
2. Download and checksum the chosen export.
3. Inspect its table of contents before restoring.
4. Restore to the isolated target using the official Render command for the
   export format.
5. Apply the same validation and cutover steps as PITR.

## Monthly restore drill evidence

Record:

```text
date / operator
source backup timestamp and checksum
target isolated database
restore start/end time
schema migration head
critical table row counts
smoke-test result
measured RPO and RTO
follow-up actions
```

A backup is not considered operationally valid until a restore drill has proven
that it can boot the current application and preserve the critical invariants.
