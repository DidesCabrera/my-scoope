def test_homepage_loads(page, base_url):
    page.goto(f"{base_url}/")
    assert page.title() is not None
