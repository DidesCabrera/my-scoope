def test_dpm_food_picker_quantity_updates_preview(page, dpm_deepedit_url, ui_settle, open_dpm_food_picker):
    page.goto(dpm_deepedit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"
    open_dpm_food_picker(page)

    food_search = page.locator("#food-search")
    food_list = page.locator("#food-list")
    quantity_input = page.locator("#food-quantity")
    meal_result_kcal = page.locator('[data-scope="dpm-meal-result"] [data-role="result-kcal"]')
    dailyplan_result_kcal = page.locator('[data-scope="dpm-dailyplan-result"] [data-role="result-kcal"]')

    food_search.fill("Pechuga Pollo Cocida")
    ui_settle(page)

    food_list.locator("li").first.click()
    ui_settle(page)

    initial_meal_kcal = meal_result_kcal.text_content()
    initial_dailyplan_kcal = dailyplan_result_kcal.text_content()

    quantity_input.fill("250")
    ui_settle(page)

    updated_meal_kcal = meal_result_kcal.text_content()
    updated_dailyplan_kcal = dailyplan_result_kcal.text_content()

    assert initial_meal_kcal != updated_meal_kcal, "La comida resultante no cambió al modificar la cantidad"
    assert initial_dailyplan_kcal != updated_dailyplan_kcal, "El plan resultante no cambió al modificar la cantidad"
