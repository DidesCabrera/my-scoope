def test_dpm_food_picker_cancel_resets_state(page, dpm_deepedit_url, ui_settle):
    page.goto(dpm_deepedit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    food_search = page.locator("#food-search")
    food_list = page.locator("#food-list")
    food_preview = page.locator("#food-preview")
    add_button = page.locator("#btn-add-food")
    cancel_button = page.locator("#btn-cancel-edit")
    quantity_input = page.locator("#food-quantity")

    food_search.wait_for()
    food_search.fill("Pechuga Pollo Cocida")

    ui_settle(page)

    first_result = food_list.locator("li").first
    first_result.wait_for()
    first_result.click()

    ui_settle(page)

    assert food_preview.is_visible(), "El preview no se mostró tras seleccionar un alimento"
    assert add_button.is_visible(), "El botón agregar no se mostró tras seleccionar un alimento"

    quantity_input.fill("250")
    ui_settle(page)

    cancel_button.wait_for()
    cancel_button.click()

    ui_settle(page)

    assert not food_preview.is_visible(), "El preview siguió visible después de cancelar"
    assert not add_button.is_visible(), "El botón agregar siguió visible después de cancelar"
    assert not food_list.is_visible(), "La lista siguió visible después de cancelar"

    current_search_value = food_search.input_value()
    assert current_search_value == "", f"El buscador no se limpió al cancelar: {current_search_value!r}"