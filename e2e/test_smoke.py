def test_homepage_loads(anonymous_page, base_url):
    anonymous_page.goto(f"{base_url}/")
    assert anonymous_page.title() is not None
