def test_meal_picker_shows_results_when_typing(page, dailyplan_edit_url):
    page.goto(dailyplan_edit_url)
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url, f"Redirigido a login: {page.url}"

    meal_search = page.locator("#meal-search")
    meal_list = page.locator("#meal-list")

    meal_search.wait_for()
    assert meal_search.is_visible()
    assert not meal_list.is_visible()

    meal_search.fill("Nueva Comida 2")

    items = meal_list.locator("li.food-item")
    items.first.wait_for()

    assert meal_list.is_visible(), "La lista no se mostró después de escribir en el buscador"
    assert items.count() > 0, "La búsqueda no devolvió resultados visibles"