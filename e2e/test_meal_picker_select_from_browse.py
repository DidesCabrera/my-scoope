def test_meal_picker_select_from_browse_shows_preview(page, dailyplan_edit_url, open_dailyplan_meal_picker):
    page.goto(dailyplan_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"
    open_dailyplan_meal_picker(page)

    meal_search = page.locator("#meal-search")
    meal_list = page.locator("#meal-list")
    meal_preview = page.locator("#dp-preview")
    add_button = page.locator("#btn-add-meal")
    preview_name = page.locator('[data-scope="meal-preview"] [data-role="preview-name"]')
    preview_kcal = page.locator('[data-scope="meal-preview"] [data-role="meal-kcal"]')
    hidden_input = page.locator("#dp-selected-meal-id")
    selection_cancel = page.locator("#btn-cancel-picker-inline-meal")
    dialog = page.locator("#dailyplan-picker-section")

    meal_search.wait_for()
    assert selection_cancel.is_visible(), "Cancelar no está visible al abrir Selección"
    selection_height = dialog.bounding_box()["height"]
    meal_search.click()

    assert meal_list.is_visible(), "La lista no se abrió al enfocar el input"

    items = meal_list.locator("li.meal-item")
    assert items.count() > 0, "No hay meals browseables en la lista"

    first_item = items.first
    first_item.click()

    assert not meal_list.is_visible(), "La lista no se cerró tras seleccionar una meal"
    assert meal_preview.is_visible(), "El preview no se mostró tras seleccionar una meal"
    assert add_button.is_visible(), "El botón add no apareció tras seleccionar una meal"
    assert page.locator("#dailyplan-picker-section").get_attribute("data-picker-step") == "impact"
    assert not meal_search.is_visible(), "La búsqueda siguió visible en el paso de impacto"
    assert page.locator('input[name="hour"]').is_visible(), "El paso de impacto no mostró la hora"
    assert page.locator('input[name="note"]').is_visible(), "El paso de impacto no mostró la nota"
    impact_height = dialog.bounding_box()["height"]
    assert abs(impact_height - selection_height) < 1, "El modal cambió de alto entre pasos"

    preview_name_text = (preview_name.text_content() or "").strip()
    preview_kcal_text = (preview_kcal.text_content() or "").strip()
    hidden_value = hidden_input.input_value().strip()

    assert preview_name_text != "", "El preview no mostró nombre de meal"
    assert preview_kcal_text != "", "El preview no mostró kcal"
    assert hidden_value != "", "No se pobló el hidden con la meal seleccionada"

    page.get_by_role("button", name="Cambiar selección").click()

    assert page.locator("#dailyplan-picker-section").get_attribute("data-picker-step") == "selection"
    assert selection_cancel.is_visible(), "Cancelar desapareció al regresar a Selección"
