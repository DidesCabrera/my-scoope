def test_food_picker_initial_state(page, meal_edit_url):
    page.goto(meal_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    food_search = page.locator("#food-search")
    food_list = page.locator("#food-list")
    food_preview = page.locator("#food-preview")
    add_button = page.locator("#btn-add-food")

    food_search.wait_for()

    assert food_search.is_visible()

    assert food_list.count() == 1
    assert not food_list.is_visible()

    assert food_preview.count() == 1
    assert not food_preview.is_visible()

    assert add_button.count() == 1
    assert not add_button.is_visible()