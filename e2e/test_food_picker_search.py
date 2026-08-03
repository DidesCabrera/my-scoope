def test_food_picker_shows_results_when_typing(page, meal_edit_url, ui_settle):
    page.goto(meal_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    food_search = page.locator("#food-search")
    food_list = page.locator("#food-list")

    food_search.wait_for()
    assert food_search.is_visible()
    assert not food_list.is_visible()

    food_search.fill("Pechuga Pollo Cocida")

    ui_settle(page)

    assert food_list.is_visible(), "La lista no se mostró después de escribir en el buscador"
