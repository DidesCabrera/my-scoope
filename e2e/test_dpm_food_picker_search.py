def test_dpm_food_picker_shows_results_when_typing(page, dpm_deepedit_url, ui_settle, open_dpm_food_picker):
    page.goto(dpm_deepedit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"
    open_dpm_food_picker(page)

    food_search = page.locator("#food-search")
    food_list = page.locator("#food-list")

    food_search.wait_for()
    assert food_search.is_visible()
    assert not food_list.is_visible()

    food_search.fill("Pechuga Pollo Cocida")

    ui_settle(page)

    assert food_list.is_visible(), "La lista no se mostró después de escribir en el buscador"
