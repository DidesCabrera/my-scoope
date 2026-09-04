def test_meal_picker_shows_results_when_typing(page, dailyplan_edit_url, open_dailyplan_meal_picker):
    page.goto(dailyplan_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"
    open_dailyplan_meal_picker(page)

    meal_search = page.locator("#meal-search")
    meal_list = page.locator("#meal-list")

    meal_search.wait_for()
    assert meal_search.is_visible()
    assert meal_list.is_visible(), "La biblioteca no se mostró al abrir el paso de selección"

    meal_search.fill("Nueva Comida 2")

    items = meal_list.locator("li.meal-item")
    items.first.wait_for()

    assert meal_list.is_visible(), "La lista no se mostró después de escribir en el buscador"
    assert items.count() > 0, "La búsqueda no devolvió resultados visibles"
