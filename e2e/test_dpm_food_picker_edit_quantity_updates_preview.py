def test_dpm_food_picker_edit_quantity_updates_preview(page, dpm_deepedit_url, ui_settle, open_food_edit_grid):
    page.goto(dpm_deepedit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"
    open_food_edit_grid(page)

    edit_button = page.locator('[id^="card-grid-foods-edit-"] .edit-food-btn').first
    quantity_input = page.locator("#food-quantity")
    meal_result_kcal = page.locator('[data-scope="dpm-meal-result"] [data-role="result-kcal"]')
    dailyplan_result_kcal = page.locator('[data-scope="dpm-dailyplan-result"] [data-role="result-kcal"]')
    food_preview = page.locator("#food-preview")
    update_button = page.locator("#btn-update-food")

    edit_button.wait_for()
    edit_button.click()

    ui_settle(page)

    assert food_preview.is_visible(), "El preview no se mostró al entrar en edit"
    assert update_button.is_visible(), "El botón Guardar Cambios no apareció en modo edit"

    initial_meal_kcal = meal_result_kcal.text_content()
    initial_dailyplan_kcal = dailyplan_result_kcal.text_content()

    quantity_input.wait_for()
    quantity_input.fill("120")

    ui_settle(page)

    updated_meal_kcal = meal_result_kcal.text_content()
    updated_dailyplan_kcal = dailyplan_result_kcal.text_content()

    assert initial_meal_kcal != updated_meal_kcal, "La comida resultante no cambió al modificar la cantidad en edit"
    assert initial_dailyplan_kcal != updated_dailyplan_kcal, "El plan resultante no cambió al modificar la cantidad en edit"
