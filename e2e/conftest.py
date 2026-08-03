import os

import pytest
from playwright.sync_api import expect


def _required_positive_int(name: str) -> int:
    raw_value = os.environ.get(name, "").strip()
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        pytest.skip(f"Set {name} to a deterministic fixture ID for this browser scenario.")
    return value


@pytest.fixture(scope="session")
def base_url():
    return os.environ.get("MYSCOOPE_E2E_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


@pytest.fixture(scope="session")
def login_credentials():
    login = os.environ.get("MYSCOOPE_E2E_LOGIN", "").strip()
    password = os.environ.get("MYSCOOPE_E2E_PASSWORD", "")
    if not login or not password:
        pytest.skip("Set MYSCOOPE_E2E_LOGIN and MYSCOOPE_E2E_PASSWORD for authenticated browser tests.")
    return login, password


@pytest.fixture
def meal_id():
    return _required_positive_int("MYSCOOPE_E2E_MEAL_ID")


@pytest.fixture
def dailyplan_id():
    return _required_positive_int("MYSCOOPE_E2E_DAILYPLAN_ID")


@pytest.fixture
def dailyplan_meal_id():
    return _required_positive_int("MYSCOOPE_E2E_DAILYPLAN_MEAL_ID")


@pytest.fixture
def meal_edit_url(base_url, meal_id):
    return f"{base_url}/app/meals/{meal_id}/"


@pytest.fixture
def dailyplan_edit_url(base_url, dailyplan_id):
    return f"{base_url}/app/dailyplans/{dailyplan_id}/"


@pytest.fixture
def dpm_deepedit_url(base_url, dailyplan_id, dailyplan_meal_id):
    # Historical tests keep the fixture name, but deep food editing now lives
    # in the canonical DailyPlanMeal detail surface.
    return f"{base_url}/app/dailyplans/{dailyplan_id}/meals/{dailyplan_meal_id}/"


@pytest.fixture
def ui_settle():
    def settle(page):
        page.wait_for_function(
            "document.readyState === 'complete' && !document.querySelector('[aria-busy=true]')"
        )
        page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )

    return settle


@pytest.fixture
def open_dpm_food_picker():
    def open_picker(page):
        toggle = page.locator('.js-picker-toggle[aria-controls="dpm-picker-section"]')
        toggle.wait_for()
        if toggle.get_attribute("aria-expanded") != "true":
            toggle.click()
        page.locator("#food-search").wait_for()

    return open_picker


@pytest.fixture
def open_meal_food_picker():
    def open_picker(page):
        toggle = page.locator('.js-picker-toggle[aria-controls="meal-picker-section"]')
        toggle.wait_for()
        if toggle.get_attribute("aria-expanded") != "true":
            toggle.click()
        page.locator("#food-search").wait_for()

    return open_picker


@pytest.fixture
def open_dailyplan_meal_picker():
    def open_picker(page):
        toggle = page.locator('.js-picker-toggle[aria-controls="dailyplan-picker-section"]')
        toggle.wait_for()
        if toggle.get_attribute("aria-expanded") != "true":
            toggle.click()
        page.locator("#meal-search").wait_for()

    return open_picker


@pytest.fixture
def open_food_edit_grid():
    def open_grid(page):
        tab = page.locator(
            '.card-detail-tabs--desktop .btn-desplegar[data-target^="#card-grid-foods-edit-"]'
        ).first
        tab.wait_for()
        tab.click()
        page.locator('[id^="card-grid-foods-edit-"] .edit-food-btn').first.wait_for()

    return open_grid


@pytest.fixture
def open_meal_edit_grid():
    def open_grid(page):
        tab = page.locator(
            '.card-detail-tabs--desktop .btn-desplegar[data-target^="#card-grid-meals-edit-"]'
        ).first
        tab.wait_for()
        tab.click()
        page.locator('[id^="card-grid-meals-edit-"] .edit-meal-btn').first.wait_for()

    return open_grid


def _login(context, *, base_url, credentials):
    login, password = credentials
    login_page = context.new_page()
    login_page.goto(f"{base_url}/accounts/login/")
    login_page.locator('input[name="login"]').fill(login)
    login_page.locator('input[name="password"]').fill(password)
    login_page.get_by_role("button").click()
    expect(login_page).not_to_have_url(f"{base_url}/accounts/login/")
    login_page.close()


@pytest.fixture(scope="session")
def authenticated_storage_state(browser, base_url, login_credentials):
    authenticated_context = browser.new_context()
    _login(
        authenticated_context,
        base_url=base_url,
        credentials=login_credentials,
    )
    storage_state = authenticated_context.storage_state()
    authenticated_context.close()
    return storage_state


@pytest.fixture
def context(browser, authenticated_storage_state):
    context = browser.new_context(storage_state=authenticated_storage_state)
    yield context
    context.close()


@pytest.fixture
def page(context):
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture
def anonymous_page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()
