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

Authenticated scenarios additionally require credentials supplied through the
environment. No real password or persisted browser state belongs in Git:

```bash
MYSCOOPE_E2E_LOGIN=local-test@example.com \
MYSCOOPE_E2E_PASSWORD=local-only-password \
scripts/test_e2e.sh
```

TDG07 owns the migration from historical fixed object IDs and sleeps to generated
fixtures and observable browser conditions. Until that patch, the broad historical
suite is local/manual evidence rather than a required CI gate.
