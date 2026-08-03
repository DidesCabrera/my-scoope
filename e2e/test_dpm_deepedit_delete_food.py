def test_dpm_deepedit_delete_food_removes_row(page, dpm_deepedit_url, ui_settle):
    page.goto(dpm_deepedit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    edit_buttons = page.locator(".edit-food-btn")
    initial_count = edit_buttons.count()

    assert initial_count > 0, "No hay filas para borrar en la tabla de foods"

    first_row = page.locator("table.table-foods--dpm tbody tr").first
    first_row.wait_for()

    delete_button = first_row.locator('button[type="submit"]').first
    delete_button.wait_for()
    delete_button.click()

    page.wait_for_load_state("networkidle")
    ui_settle(page)

    assert "/deepedit/" in page.url, f"La vista no volvió a deepedit: {page.url}"

    updated_count = page.locator(".edit-food-btn").count()

    assert updated_count == initial_count - 1, (
        f"La cantidad de filas no disminuyó tras borrar. "
        f"Antes: {initial_count}, después: {updated_count}"
    )