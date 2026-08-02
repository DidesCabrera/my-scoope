def test_login_and_save_state(page, base_url, login_credentials, auth_state_file):
    login, password = login_credentials
    page.goto(f"{base_url}/accounts/login/")

    page.locator('input[name="login"]').fill(login)
    page.locator('input[name="password"]').fill(password)
    page.get_by_role("button").click()

    page.wait_for_load_state("networkidle")

    # Verifica que NO sigues en login
    assert "/accounts/login/" not in page.url

    # Verifica acceso real a la aplicación sin acoplar el smoke a IDs locales.
    page.goto(f"{base_url}/app/")
    page.wait_for_load_state("networkidle")

    assert "/accounts/login/" not in page.url

    auth_state_file.parent.mkdir(parents=True, exist_ok=True)
    page.context.storage_state(path=str(auth_state_file))
