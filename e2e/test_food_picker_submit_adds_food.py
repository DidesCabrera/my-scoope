def test_food_picker_submit_adds_food(page, meal_edit_url, ui_settle, open_meal_food_picker):
    page.goto(meal_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"
    open_meal_food_picker(page)

    food_search = page.locator("#food-search")
    food_list = page.locator("#food-list")
    food_preview = page.locator("#food-preview")
    quantity_input = page.locator("#food-quantity")
    add_button = page.locator("#btn-add-food")

    food_search.wait_for()
    food_search.fill("Pechuga Pollo Cocida")

    ui_settle(page)

    first_result = food_list.locator("li").first
    first_result.wait_for()
    first_result.click()

    ui_settle(page)

    assert food_preview.is_visible(), "El preview no se mostró tras seleccionar un alimento"

    quantity_input.wait_for()
    quantity_input.fill("250")

    ui_settle(page)

    add_button.wait_for()
    add_button.click()

    page.wait_for_load_state("networkidle")
    ui_settle(page)

    assert "Pechuga Pollo Cocida" in page.content(), (
        "El alimento no apareció en la página después de agregarlo"
    )
