def test_food_picker_edit_quantity_updates_preview(page, meal_edit_url, ui_settle, open_food_edit_grid):
    page.goto(meal_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"
    open_food_edit_grid(page)

    edit_button = page.locator('[id^="card-grid-foods-edit-"] .edit-food-btn').first
    quantity_input = page.locator("#food-quantity")
    qty_kcal = page.locator("#qty-kcal")
    food_preview = page.locator("#food-preview")
    update_button = page.locator("#btn-update-food")

    edit_button.wait_for()
    edit_button.click()

    ui_settle(page)

    assert food_preview.is_visible(), "El preview no se mostró al entrar en edit"
    assert update_button.is_visible(), "El botón Guardar Cambios no apareció en modo edit"

    initial_kcal = qty_kcal.text_content()
    initial_quantity = float(quantity_input.input_value())

    quantity_input.wait_for()
    quantity_input.fill(str(initial_quantity + 25))

    ui_settle(page)

    updated_kcal = qty_kcal.text_content()

    assert initial_kcal is not None and initial_kcal.strip() != ""
    assert updated_kcal is not None and updated_kcal.strip() != ""
    assert initial_kcal != updated_kcal, "Las kcal no cambiaron al modificar la cantidad en edit"
