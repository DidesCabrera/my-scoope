def test_dpm_food_picker_quantity_updates_preview(page, dpm_deepedit_url, ui_settle):
    page.goto(dpm_deepedit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    food_search = page.locator("#food-search")
    food_list = page.locator("#food-list")
    quantity_input = page.locator("#food-quantity")
    qty_kcal = page.locator("#qty-kcal")

    food_search.fill("Pechuga Pollo Cocida")
    ui_settle(page)

    food_list.locator("li").first.click()
    ui_settle(page)

    initial_kcal = qty_kcal.text_content()

    quantity_input.fill("250")
    ui_settle(page)

    updated_kcal = qty_kcal.text_content()

    assert initial_kcal != updated_kcal, "Las kcal no cambiaron al modificar la cantidad"