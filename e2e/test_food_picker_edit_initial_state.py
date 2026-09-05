def test_food_picker_edit_initial_state(page, meal_edit_url, ui_settle, open_food_edit_grid):
    page.goto(meal_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    form_title = page.locator("#food-form-title")
    food_preview = page.locator("#food-preview")
    add_button = page.locator("#btn-add-food")
    update_button = page.locator("#btn-update-food")
    quantity_input = page.locator("#food-quantity")
    form_preview = page.locator("#form-preview")

    form_title.wait_for(state="attached")

    assert form_title.text_content().strip() == "Agrega un Alimento"
    assert not food_preview.is_visible()
    assert not add_button.is_visible()
    assert not update_button.is_visible()
    open_food_edit_grid(page)

    edit_button = page.locator('[id^="card-grid-foods-edit-"] .edit-food-btn').first
    edit_button.wait_for()
    edit_button.click()

    ui_settle(page)

    assert form_title.text_content().strip() == "Edita el Alimento"
    assert food_preview.is_visible(), "El preview no se mostró al entrar en edit"
    assert update_button.is_visible(), "El botón Guardar Cambios no apareció en modo edit"
    assert not add_button.is_visible(), "El botón Agregar Alimento siguió visible en modo edit"

    qty_value = quantity_input.input_value()
    assert qty_value.strip() != "", "La cantidad no se precargó en modo edit"

    current_action = form_preview.get_attribute("action")
    assert current_action is not None
    assert "/mealfoods/" in current_action and current_action.endswith("/update/")
