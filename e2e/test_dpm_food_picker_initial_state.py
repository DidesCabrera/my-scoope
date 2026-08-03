def test_dpm_food_picker_initial_state(page, dpm_deepedit_url, open_dpm_food_picker):
    page.goto(dpm_deepedit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    food_search = page.locator("#food-search")
    food_list = page.locator("#food-list")
    food_preview = page.locator("#food-preview")
    add_button = page.locator("#btn-add-food")

    assert food_search.count() == 1
    assert not food_search.is_visible()

    assert food_list.count() == 1
    assert not food_list.is_visible()

    assert food_preview.count() == 1
    assert not food_preview.is_visible()

    assert add_button.count() == 1
    assert not add_button.is_visible()

    open_dpm_food_picker(page)
    assert food_search.is_visible()
