def test_food_picker_initial_state(page, meal_edit_url, open_meal_food_picker):
    page.goto(meal_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    food_search = page.locator("#food-search")
    food_list = page.locator("#food-list")
    food_preview = page.locator("#food-preview")
    add_button = page.locator("#btn-add-food")
    dialog = page.locator("#meal-picker-section")
    underlying_panel = page.locator(".content-panel.content-panel--main").first

    assert food_search.count() == 1
    assert not food_search.is_visible()

    assert food_list.count() == 1
    assert not food_list.is_visible()

    assert food_preview.count() == 1
    assert not food_preview.is_visible()

    assert add_button.count() == 1
    assert not add_button.is_visible()

    panel_y_before = underlying_panel.bounding_box()["y"]
    open_meal_food_picker(page)
    panel_y_after = underlying_panel.bounding_box()["y"]

    assert dialog.get_attribute("open") is not None
    assert dialog.get_attribute("data-picker-step") == "selection"
    assert abs(panel_y_after - panel_y_before) < 1, "Abrir el modal desplazó el contenido de detalle"
    assert food_search.is_visible()
