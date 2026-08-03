# Browser smoke tests

The browser suite is a separate quality surface from Django's test runner.

Install its Python runtime and Chromium:

```bash
python -m pip install -r e2e/requirements.txt
python -m playwright install chromium
```

Run the smoke suite against an already running local server:

```bash
MYSCOOPE_E2E_BASE_URL=http://127.0.0.1:8000 scripts/test_e2e.sh
```

Authenticated scenarios require credentials supplied through the environment. The
suite logs in once, reuses an in-memory Playwright storage snapshot for isolated
contexts and never writes authentication state to disk or Git:

```bash
MYSCOOPE_E2E_LOGIN=local-test@example.com \
MYSCOOPE_E2E_PASSWORD=local-only-password \
scripts/test_e2e.sh
```

Object-specific scenarios additionally use deterministic fixture IDs instead of IDs
embedded in test code:

```bash
MYSCOOPE_E2E_MEAL_ID=222 \
MYSCOOPE_E2E_DAILYPLAN_ID=122 \
MYSCOOPE_E2E_DAILYPLAN_MEAL_ID=343 \
scripts/test_e2e.sh
```

Create a complete disposable local fixture graph and export its emitted IDs before
running the full suite:

```bash
python manage.py seed_e2e_fixtures \
  --login local-test@example.com \
  --password local-only-password \
  --github-env > /tmp/my-scoope-e2e.env
set -a
source /tmp/my-scoope-e2e.env
set +a
scripts/test_e2e.sh
```

CI runs both the anonymous smoke and every authenticated scenario against a fresh
database seeded by this command. Its committed credential is disposable and exists
only inside the ephemeral runner database.
