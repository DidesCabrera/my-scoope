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

Authenticated scenarios log in afresh and require credentials supplied through the
environment. No real password or persisted browser state belongs in Git:

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

The anonymous homepage smoke is the CI-owned browser gate. The broader authenticated
suite remains explicit local/staging evidence because it needs seeded scenario data.
