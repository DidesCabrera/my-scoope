def test_food_composition_picker_fits_mobile_viewport(
    page,
    meal_edit_url,
    open_meal_food_picker,
):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(meal_edit_url)
    page.wait_for_load_state("networkidle")

    underlying_panel = page.locator(".content-panel.content-panel--main").first
    panel_y_before = underlying_panel.bounding_box()["y"]

    open_meal_food_picker(page)

    dialog = page.locator("#meal-picker-section")
    bounds = dialog.bounding_box()
    panel_y_after = underlying_panel.bounding_box()["y"]

    assert bounds is not None
    assert bounds["x"] >= 0
    assert bounds["y"] >= 0
    assert bounds["x"] + bounds["width"] <= 390.5
    assert bounds["y"] + bounds["height"] <= 844.5
    assert dialog.get_attribute("data-picker-step") == "selection"
    assert page.locator("#food-search").is_visible()
    assert page.get_by_role("link", name="Crear alimento").is_visible()
    assert abs(panel_y_after - panel_y_before) < 1
