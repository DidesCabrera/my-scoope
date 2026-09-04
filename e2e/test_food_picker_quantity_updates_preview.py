def test_food_picker_quantity_updates_preview(page, meal_edit_url, ui_settle, open_meal_food_picker):
    page.goto(meal_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"
    open_meal_food_picker(page)

    food_search = page.locator("#food-search")
    food_list = page.locator("#food-list")
    quantity_input = page.locator("#food-quantity")
    qty_kcal = page.locator("#qty-kcal")
    result_kcal = page.locator('[data-scope="meal-result"] [data-role="result-kcal"]')

    food_search.wait_for()
    food_search.fill("Pechuga Pollo Cocida")

    ui_settle(page)

    first_result = food_list.locator("li").first
    first_result.wait_for()
    first_result.click()

    ui_settle(page)

    initial_kcal = qty_kcal.text_content()
    initial_result_kcal = result_kcal.text_content()

    quantity_input.wait_for()
    quantity_input.fill("250")

    ui_settle(page)

    updated_kcal = qty_kcal.text_content()
    updated_result_kcal = result_kcal.text_content()

    assert initial_kcal is not None and initial_kcal.strip() != ""
    assert updated_kcal is not None and updated_kcal.strip() != ""
    assert initial_kcal != updated_kcal, "Las kcal no cambiaron al modificar la cantidad"
    assert initial_result_kcal != updated_result_kcal, (
        "La card de la comida resultante no se actualizó con la cantidad"
    )
