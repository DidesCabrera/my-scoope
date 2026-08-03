def test_meal_picker_cancel_edit_restores_add_mode(
    page,
    dailyplan_edit_url,
    dailyplan_id,
    open_meal_edit_grid,
):
    page.goto(dailyplan_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    form_title = page.locator("#meal-form-title")
    meal_preview = page.locator("#dp-preview")
    add_button = page.locator("#btn-add-meal")
    update_button = page.locator("#btn-update-meal")
    cancel_button = page.locator("#btn-cancel-meal-edit")
    meal_search = page.locator("#meal-search")
    hidden_input = page.locator("#dp-selected-meal-id")
    form_preview = page.locator("#dp-form")

    form_title.wait_for()

    initial_action = form_preview.get_attribute("action")
    assert initial_action is not None
    assert initial_action.endswith("/add-meal/")
    open_meal_edit_grid(page)

    edit_button = page.locator('[id^="card-grid-meals-edit-"] .edit-meal-btn').first
    edit_button.wait_for()
    edit_button.click()

    assert form_title.text_content().strip() == "Reemplaza la Comida"
    assert meal_preview.is_visible()
    assert update_button.is_visible()
    assert not add_button.is_visible()

    cancel_button.click()

    assert form_title.text_content().strip() == "Agrega una Comida"
    assert not meal_preview.is_visible(), "El preview siguió visible después de cancelar"
    assert not update_button.is_visible(), "El botón update siguió visible después de cancelar"
    assert not add_button.is_visible(), "El botón add no debería verse si el preview está oculto"

    assert meal_search.input_value() == "", "El input de búsqueda no se limpió"
    assert hidden_input.input_value() == "", "El hidden de meal seleccionada no se limpió"

    action_after_cancel = form_preview.get_attribute("action")
    assert action_after_cancel is not None
    assert action_after_cancel.endswith(f"/app/dailyplans/{dailyplan_id}/add-meal/"), (
        f"El form.action no volvió al add action. "
        f"Obtenido={action_after_cancel}"
    )
