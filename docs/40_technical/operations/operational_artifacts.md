# Operational Artifacts

Status: current
Last updated: 2026-07-18

## Purpose

Keep generated evidence useful without mixing current source, local data, and
historical reports in the repository root.

## Locations

```text
artifacts/local/          ignored local reports, diagnostics and temporary exports
artifacts/staging/        ignored downloaded staging evidence
docs/90_archive/reports/  intentionally preserved, reviewed historical evidence
```

SQLite databases and backups remain local and ignored. A backup is not a migration,
fixture, seed, or catalog source and must never be committed as one.

## Report lifecycle

1. Generate new reports under `artifacts/local/` by default.
2. Review and sanitize them before sharing.
3. Promote only durable, non-sensitive evidence to `docs/90_archive/reports/` through
   an explicit documentation patch.
4. Never store API keys, provider payloads, private user data, prompts, or OAuth
   credentials in an artifact.

The root-level CM24/PT JSON files predate this policy. They remain an explicit legacy
allowlist so history is preserved; new root-level `*_report*.json` files fail the
repository hygiene gate.

Example:

```bash
python manage.py validate_ai_assistant_real_provider \
  --live --user-id <STAGING_USER_ID> \
  --output artifacts/local/cm24_real_provider_report.json
```

