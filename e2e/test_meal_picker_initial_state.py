def test_meal_picker_initial_state(page, dailyplan_edit_url, open_dailyplan_meal_picker):
    page.goto(dailyplan_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    meal_search = page.locator("#meal-search")
    meal_list = page.locator("#meal-list")
    meal_preview = page.locator("#dp-preview")
    add_button = page.locator("#btn-add-meal")
    update_button = page.locator("#btn-update-meal")
    form_title = page.locator("#meal-form-title")

    assert meal_search.count() == 1
    assert not meal_search.is_visible()
    assert form_title.text_content().strip() == "Agrega una Comida"

    assert meal_list.count() == 1
    assert not meal_list.is_visible()

    assert not meal_preview.is_visible()
    assert not add_button.is_visible()
    assert not update_button.is_visible()

    open_dailyplan_meal_picker(page)
    assert meal_search.is_visible()
