def test_dpm_deepedit_delete_food_removes_row(page, dpm_deepedit_url, ui_settle, open_food_edit_grid):
    page.goto(dpm_deepedit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"
    open_food_edit_grid(page)

    edit_buttons = page.locator('[id^="card-grid-foods-edit-"] .edit-food-btn')
    initial_count = edit_buttons.count()

    assert initial_count > 0, "No hay filas para borrar en la tabla de foods"

    first_row = edit_buttons.first.locator(
        "xpath=ancestor::*[contains(@class, 'data-grid-row--foods-edit')]"
    )
    first_row.wait_for()

    delete_button = first_row.locator('button[type="submit"]').first
    delete_button.wait_for()
    delete_button.click()

    page.wait_for_load_state("networkidle")
    ui_settle(page)

    assert "/dailyplans/" in page.url and "/meals/" in page.url, (
        f"La vista no volvió al detalle editable: {page.url}"
    )

    updated_count = page.locator('[id^="card-grid-foods-edit-"] .edit-food-btn').count()

    assert updated_count == initial_count - 1, (
        f"La cantidad de filas no disminuyó tras borrar. "
        f"Antes: {initial_count}, después: {updated_count}"
    )
