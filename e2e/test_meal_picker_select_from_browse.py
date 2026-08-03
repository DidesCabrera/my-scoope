def test_meal_picker_select_from_browse_shows_preview(page, dailyplan_edit_url):
    page.goto(dailyplan_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    meal_search = page.locator("#meal-search")
    meal_list = page.locator("#meal-list")
    meal_preview = page.locator("#dp-preview")
    add_button = page.locator("#btn-add-meal")
    preview_name = page.locator('[data-scope="meal-preview"] [data-role="preview-name"]')
    preview_kcal = page.locator('[data-scope="meal-preview"] [data-role="meal-kcal"]')
    hidden_input = page.locator("#dp-selected-meal-id")

    meal_search.wait_for()
    meal_search.click()

    assert meal_list.is_visible(), "La lista no se abrió al enfocar el input"

    items = meal_list.locator("li.food-item")
    assert items.count() > 0, "No hay meals browseables en la lista"

    first_item = items.first
    first_item.click()

    assert not meal_list.is_visible(), "La lista no se cerró tras seleccionar una meal"
    assert meal_preview.is_visible(), "El preview no se mostró tras seleccionar una meal"
    assert add_button.is_visible(), "El botón add no apareció tras seleccionar una meal"

    preview_name_text = (preview_name.text_content() or "").strip()
    preview_kcal_text = (preview_kcal.text_content() or "").strip()
    hidden_value = hidden_input.input_value().strip()

    assert preview_name_text != "", "El preview no mostró nombre de meal"
    assert preview_kcal_text != "", "El preview no mostró kcal"
    assert hidden_value != "", "No se pobló el hidden con la meal seleccionada"