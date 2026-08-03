def test_food_picker_selecting_food_shows_preview(page, meal_edit_url, ui_settle, open_meal_food_picker):
    page.goto(meal_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"
    open_meal_food_picker(page)

    food_search = page.locator("#food-search")
    food_list = page.locator("#food-list")
    food_preview = page.locator("#food-preview")
    add_button = page.locator("#btn-add-food")

    food_search.wait_for()
    food_search.fill("Pechuga Pollo Cocida")

    ui_settle(page)

    assert food_list.is_visible(), "La lista no se mostró después de escribir"

    first_result = food_list.locator("li").first
    first_result.wait_for()
    first_result.click()

    ui_settle(page)

    assert food_preview.is_visible(), "El preview no se mostró tras seleccionar un alimento"
    assert add_button.is_visible(), "El botón de agregar no se mostró tras seleccionar un alimento"
