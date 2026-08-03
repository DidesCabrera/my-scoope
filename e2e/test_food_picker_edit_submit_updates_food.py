def test_food_picker_edit_submit_updates_food(page, meal_edit_url, ui_settle, open_food_edit_grid):
    page.goto(meal_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"
    open_food_edit_grid(page)

    edit_button = page.locator('[id^="card-grid-foods-edit-"] .edit-food-btn').first
    quantity_input = page.locator("#food-quantity")
    update_button = page.locator("#btn-update-food")

    edit_button.wait_for()
    edit_button.click()

    ui_settle(page)

    quantity_input.wait_for()
    quantity_input.fill("120")

    ui_settle(page)

    update_button.wait_for()
    update_button.click()

    page.wait_for_load_state("networkidle")
    ui_settle(page)

    assert "120" in page.content(), "La nueva cantidad no apareció en la página después de guardar cambios"
