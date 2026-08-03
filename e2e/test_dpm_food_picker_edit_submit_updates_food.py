def test_dpm_food_picker_edit_submit_updates_food(page, dpm_deepedit_url, ui_settle):
    page.goto(dpm_deepedit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    edit_button = page.locator(".edit-food-btn").first
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
    assert "/update/" not in page.url or "404" not in page.content()