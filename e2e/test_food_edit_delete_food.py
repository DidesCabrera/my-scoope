def test_food_edit_delete_food_removes_row(page, meal_edit_url):
    page.goto(meal_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    edit_buttons = page.locator(".edit-food-btn")
    initial_count = edit_buttons.count()

    assert initial_count > 0, "No hay filas para borrar en la tabla de foods"

    first_edit_button = edit_buttons.first
    first_edit_button.wait_for()

    first_row = first_edit_button.locator(
        "xpath=ancestor::*[contains(@class, 'data-grid-row--foods-edit')]"
    )
    delete_button = first_row.locator('button[type="submit"]').first

    delete_button.wait_for()
    delete_button.click()

    page.wait_for_load_state("networkidle")

    new_count = page.locator(".edit-food-btn").count()
    assert new_count == initial_count - 1