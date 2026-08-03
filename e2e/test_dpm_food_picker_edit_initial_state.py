def test_dpm_food_picker_edit_initial_state(page, dpm_deepedit_url, ui_settle):
    messages = []

    page.on("console", lambda msg: messages.append(f"{msg.type}: {msg.text}"))

    page.goto(dpm_deepedit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    form_title = page.locator("#food-form-title")
    food_preview = page.locator("#food-preview")
    add_button = page.locator("#btn-add-food")
    update_button = page.locator("#btn-update-food")

    form_title.wait_for()

    assert form_title.text_content().strip() == "Agrega un Alimento"
    assert not food_preview.is_visible()
    assert not add_button.is_visible()
    assert not update_button.is_visible()

    edit_button = page.locator(".edit-food-btn").first
    edit_button.wait_for()
    edit_button.click()

    ui_settle(page)

    print("\n".join(messages))

    assert form_title.text_content().strip() == "Edita el Alimento"
    assert food_preview.is_visible(), "El preview no se mostró al entrar en edit"