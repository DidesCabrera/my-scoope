import os
from pathlib import Path

import pytest


DEFAULT_STATE_FILE = Path("e2e/auth/state.json")


@pytest.fixture
def base_url():
    return os.environ.get("MYSCOOPE_E2E_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


@pytest.fixture
def login_credentials():
    login = os.environ.get("MYSCOOPE_E2E_LOGIN", "").strip()
    password = os.environ.get("MYSCOOPE_E2E_PASSWORD", "")
    if not login or not password:
        pytest.skip("Set MYSCOOPE_E2E_LOGIN and MYSCOOPE_E2E_PASSWORD for authenticated browser tests.")
    return login, password


@pytest.fixture
def auth_state_file() -> Path:
    configured = os.environ.get("MYSCOOPE_E2E_AUTH_STATE_FILE", "").strip()
    return Path(configured) if configured else DEFAULT_STATE_FILE


@pytest.fixture
def context(browser, request, auth_state_file):
    test_file = str(request.node.fspath)

    # El test de login debe correr sin sesión previa
    if "test_login_and_save_state.py" in test_file:
        context = browser.new_context()
        yield context
        context.close()
        return

    if not auth_state_file.exists():
        pytest.fail(
            f"Falta {auth_state_file}. Primero corre el test de login para guardar la sesión."
        )

    context = browser.new_context(storage_state=str(auth_state_file))
    yield context
    context.close()


@pytest.fixture
def page(context):
    page = context.new_page()
    yield page
    page.close()
