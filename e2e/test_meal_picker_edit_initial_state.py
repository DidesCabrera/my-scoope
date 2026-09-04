def test_meal_picker_edit_initial_state(
    page,
    dailyplan_edit_url,
    ui_settle,
    dailyplan_id,
    open_meal_edit_grid,
):
    page.goto(dailyplan_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    form_title = page.locator("#meal-form-title")
    meal_preview = page.locator("#dp-preview")
    add_button = page.locator("#btn-add-meal")
    update_button = page.locator("#btn-update-meal")
    form_preview = page.locator("#dp-form")
    preview_name = page.locator('[data-scope="meal-preview"] [data-role="preview-name"]')

    form_title.wait_for(state="attached")

    assert form_title.text_content().strip() == "Agrega una Comida"
    assert not meal_preview.is_visible()
    assert not add_button.is_visible()
    assert not update_button.is_visible()
    open_meal_edit_grid(page)

    edit_button = page.locator('[id^="card-grid-meals-edit-"] .edit-meal-btn').first
    edit_button.wait_for()
    edit_button.click()

    ui_settle(page)

    title_after = form_title.text_content().strip()
    preview_visible = meal_preview.is_visible()
    update_visible = update_button.is_visible()
    add_visible = add_button.is_visible()
    action_after = form_preview.get_attribute("action")
    preview_text = (preview_name.text_content() or "").strip()

    assert title_after == "Reemplaza la Comida", f"Título inesperado tras editar: {title_after}"
    assert preview_visible, f"El preview sigue oculto. action={action_after}, preview_text='{preview_text}'"
    assert update_visible, "El botón update no apareció"
    assert not add_visible, "El botón add siguió visible"

    assert preview_text != "", "No se cargó el nombre de la meal en el preview"

    assert action_after is not None
    assert f"/dailyplans/{dailyplan_id}/meals/" in action_after and action_after.endswith("/update/")
