# Food Catalog authority and release runbook

Status: current
Date: 2026-09-17

## Render topology

`render.catalog.yaml` declares:

```text
myscoope-food-catalog       Django authority web service, Starter
myscoope-food-catalog-db    independent PostgreSQL, Basic 256 MB
```

The authority deploys from `staging` during initial validation. After the same
code reaches `main`, update the service branch to `main`. Do not create a second
authority. A permanent worker is not required for this volume; use Render one-off
shell jobs for bootstrap, publication and release operations.

Required authority settings:

```text
DJANGO_SETTINGS_MODULE=miapp.settings.catalog
DATABASE_URL=<authority database>
SECRET_KEY=<independent random secret of at least 50 characters>
FOOD_CATALOG_RELEASE_TOKEN=<shared random secret>
FOOD_CATALOG_AUTHORITY_EXPORT_ENABLED=false
```

`SECRET_KEY` is intentionally `sync: false` in the authority blueprint. Render's
generated value is currently 44 characters, which Django 6 flags as too short.
Create an independent secret of at least 50 characters during provisioning; do
not reuse the release token.

Required on each consumer web service:

```text
FOOD_CATALOG_RELEASE_URL=https://myscoope-food-catalog.onrender.com
FOOD_CATALOG_RELEASE_TOKEN=<same shared random secret>
```

Do not distribute the token to unrelated workers. Rotate it by updating authority
and consumers before the next release import. Never place it in Git or command logs.

## Initial authority bootstrap

### 1. Preconditions

- the authority health endpoint returns 200;
- authority migrations completed;
- authority has zero `CatalogFood` rows;
- staging has the expected 219 rows and their import-batch/source/portion/alias evidence;
- the same release token exists on authority and staging web;
- `FOOD_CATALOG_AUTHORITY_EXPORT_ENABLED` remains false except during steps 2-3.

### 2. Temporarily open the protected staging export

Set `FOOD_CATALOG_AUTHORITY_EXPORT_ENABLED=true` on staging and wait for its
redeploy. The endpoint still requires the bearer token.

### 3. Import into the empty authority

Run in the authority shell:

```text
python manage.py import_catalog_authority_snapshot \
  --url https://myscoope-staging.onrender.com/internal/food-catalog/authority-snapshot/export/
```

Reconcile the returned count, then immediately set the staging flag to `false`
and verify the endpoint returns 404. The import refuses a non-empty catalog, so it
cannot be used as a general synchronization mechanism.

### 4. Create an audit actor

Create an authority-only user with a real internal operator email. A password is
not needed for command-only operation; if Django Admin access is required, set a
strong password through Render's protected shell and normal account procedures.

### 5. Publish the verified batch

```text
python manage.py publish_verified_catalog_foods
python manage.py publish_verified_catalog_foods \
  --apply --actor-email <operator-email>
```

The first command is a dry run. Any invalid food blocks the entire apply.

### 6. Build and approve the initial release

Use a monotonically increasing immutable version, for example `2026.09.1`:

```text
python manage.py build_catalog_release \
  --release-version 2026.09.1 \
  --actor-email <operator-email> \
  --notes "Initial central authority release"

python manage.py approve_catalog_release \
  --release-version 2026.09.1 \
  --actor-email <operator-email>
```

Record the printed count and SHA-256 in the deployment evidence.

### 7. Validate and import into staging

Run in the staging web shell:

```text
python manage.py import_food_catalog_release \
  --release-version 2026.09.1 --dry-run

python manage.py import_food_catalog_release \
  --release-version 2026.09.1 --materialize
```

Confirm the imported release count and that the expected global operational foods
are visible to the same query layer used by Solver, MCP and AI. Repeating the
command must report an idempotent import and create no duplicate foods.

## Recurring release workflow

1. Import/acquire and curate only in the authority.
2. Publish reviewed/verified foods explicitly.
3. Build a new candidate version and review count/checksum/notes.
4. Approve the candidate.
5. Dry-run, import and smoke-test in staging.
6. Import the identical version in production only after staging acceptance.
7. Retain release records and evidence; never edit an approved payload.

For a nutrition correction, increment the food's `catalog_version`, build a new
release and import it. The current reusable operational food is refreshed in place;
existing composed entities are not rebuilt automatically.

## Failure and rollback

- checksum/schema/count failure: no data is written; correct the transport or issue a new release;
- partial database failure: the transaction rolls back;
- bad candidate before approval: discard/revoke it and build another version;
- bad approved release: do not mutate it; correct the authority and issue a newer release;
- authority unavailable: consumers keep serving their local data; postpone imports;
- token exposure: rotate on authority and consumers before another import;
- bootstrap mismatch: stop before publication, keep staging export off, and restore/recreate only the empty authority database according to the PostgreSQL restore runbook.

## Reconciliation checklist

- authority food count by status matches bootstrap evidence;
- approved release count equals published authority count;
- consumer replica stores the same version, count and SHA-256;
- every delivered mirror has `is_release_managed=true` and the release version;
- materialization has no duplicate `catalog_food_id` links;
- second import is idempotent;
- staging snapshot export is disabled;
- no consumer request path calls the authority.
