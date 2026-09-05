def test_food_picker_selecting_food_shows_preview(page, meal_edit_url, ui_settle, open_meal_food_picker):
    page.goto(meal_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"
    open_meal_food_picker(page)

    food_search = page.locator("#food-search")
    food_list = page.locator("#food-list")
    food_preview = page.locator("#food-preview")
    add_button = page.locator("#btn-add-food")
    selection_cancel = page.locator("#btn-cancel-picker-inline-food")
    dialog = page.locator("#meal-picker-section")

    food_search.wait_for()
    assert selection_cancel.is_visible(), "Cancelar no está visible al abrir Selección"
    selection_height = dialog.bounding_box()["height"]
    food_search.fill("Pechuga Pollo Cocida")

    ui_settle(page)

    assert food_list.is_visible(), "La lista no se mostró después de escribir"

    first_result = food_list.locator("li").first
    first_result.wait_for()
    first_result.click()

    ui_settle(page)

    assert food_preview.is_visible(), "El preview no se mostró tras seleccionar un alimento"
    assert add_button.is_visible(), "El botón de agregar no se mostró tras seleccionar un alimento"
    assert page.locator("#meal-picker-section").get_attribute("data-picker-step") == "impact"
    assert not food_search.is_visible(), "La búsqueda siguió visible en el paso de impacto"
    result_card = page.locator('[data-scope="meal-result"]')
    projected_item = result_card.locator(".is-visible [data-projected='true']")
    assert result_card.is_visible(), "No se mostró la card de la comida resultante"
    assert projected_item.count() == 1, "La card no destacó el alimento por agregar"
    assert "Por agregar" in (projected_item.text_content() or "")
    impact_height = dialog.bounding_box()["height"]
    assert abs(impact_height - selection_height) < 1, "El modal cambió de alto entre pasos"

    page.get_by_role("button", name="Cambiar selección").click()

    assert page.locator("#meal-picker-section").get_attribute("data-picker-step") == "selection"
    assert food_search.is_visible(), "Cambiar selección no regresó a la biblioteca"
    assert selection_cancel.is_visible(), "Cancelar desapareció al regresar a Selección"
