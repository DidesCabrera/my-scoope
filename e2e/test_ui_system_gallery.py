from playwright.sync_api import expect


def test_web_ui_system_uses_product_components_and_real_mobile_media_queries(
    anonymous_page,
    base_url,
    ui_settle,
):
    anonymous_page.goto(f"{base_url}/app/dev/ui-system/")
    ui_settle(anonymous_page)

    expect(anonymous_page.get_by_role("heading", name="UI System Web")).to_be_visible()
    expect(anonymous_page.locator(".dash-kpi-comp").first).to_be_visible()
    expect(anonymous_page.locator(".program-card").first).to_be_visible()

    total_geometry = anonymous_page.locator(".dash-kpi-comp .tot").first.evaluate(
        """element => {
            const style = getComputedStyle(element);
            return {
                flexBasis: style.flexBasis,
                borderWidth: style.borderTopWidth,
                borderRadius: style.borderRadius,
                height: element.getBoundingClientRect().height,
            };
        }"""
    )
    assert total_geometry == {
        "flexBasis": "96px",
        "borderWidth": "3px",
        "borderRadius": "22px",
        "height": 96,
    }

    mobile_frame = anonymous_page.frame_locator(".ui-system-gallery__mobile-frame")
    expect(mobile_frame.locator(".dash-kpi-comp").first).to_be_visible()
    responsive_state = mobile_frame.locator("body").evaluate(
        """() => ({
            width: innerWidth,
            mobileMedia: matchMedia('(max-width: 768px)').matches,
            hasProgramCard: Boolean(document.querySelector('.program-card')),
        })"""
    )
    assert responsive_state["width"] <= 390
    assert responsive_state["mobileMedia"] is True
    assert responsive_state["hasProgramCard"] is True


def test_conversation_gallery_runs_the_mcp_card_with_synthetic_states(
    anonymous_page,
    base_url,
):
    anonymous_page.set_viewport_size({"width": 1600, "height": 900})
    anonymous_page.goto(f"{base_url}/app/dev/ui-system/#conversation-ui")
    card = anonymous_page.frame_locator("#mcp-meal-frame")

    expect(card.get_by_role("heading", name="Pollo con arroz integral y ensalada")).to_be_visible()
    expect(card.locator("#meal-kcal")).to_have_text("726")
    expect(card.locator("#meal-protein-bar")).to_have_attribute("aria-label", "38%")
    expect(card.locator("#meal-carbs-bar")).to_have_attribute("aria-label", "39%")
    expect(card.locator("#meal-food-table tr")).to_have_count(4)
    expect(card.locator("#meal-food-table")).to_be_visible()
    expect(card.get_by_text("Pechuga de pollo cocida").first).to_be_visible()
    card_height = card.locator("body").evaluate("element => element.scrollHeight")
    anonymous_page.wait_for_function(
        "height => document.querySelector('#mcp-meal-frame').clientHeight >= height",
        arg=card_height,
    )

    anonymous_page.get_by_role("button", name="Claro").click()
    expect(card.locator("#card")).not_to_have_css("background-color", "rgb(18, 18, 18)")
    anonymous_page.get_by_role("button", name="Oscuro").click()
    expect(card.locator("#card")).to_have_css("background-color", "rgb(18, 18, 18)")

    anonymous_page.get_by_role("button", name="Chat web").click()
    expect(card.locator("#meal-food-table")).to_be_visible()
    expect(card.locator("#meal-foods")).to_be_hidden()
    assert card.locator("#meal-food-table tr").first.locator("td").last.evaluate(
        "element => element.getBoundingClientRect().right <= document.querySelector('.food-panel').getBoundingClientRect().right"
    )

    anonymous_page.get_by_role("button", name="Panel web").click()
    expect(card.locator("#meal-food-table")).to_be_visible()
    expect(card.locator("#meal-foods")).to_be_hidden()
    assert card.locator(".food-panel").evaluate(
        "element => element.scrollWidth > element.clientWidth"
    )
    assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")

    anonymous_page.get_by_role("button", name="Móvil").click()
    anonymous_page.locator("#mcp-meal-scenario").select_option("mobile")
    expect(card.get_by_role("heading", name="Avena con yogur, plátano y arándanos")).to_be_visible()
    expect(card.locator("#meal-kcal")).to_have_text("447")
    expect(card.locator("#meal-foods li")).to_have_count(4)
    expect(card.locator("#meal-food-table")).to_be_hidden()
    card.get_by_role("tab", name="Calorías").click()
    expect(card.locator("#card")).to_have_attribute("data-mode", "calories")
    card.get_by_role("tab", name="Macros").click()
    expect(card.locator("#card")).to_have_attribute("data-mode", "macros")
    card.get_by_role("tab", name="Dist").click()
    expect(card.locator("#card")).to_have_attribute("data-mode", "distribution")
    card.get_by_role("tab", name="Alloc").click()
    expect(card.locator("#card")).to_have_attribute("data-mode", "allocation")

    anonymous_page.get_by_role("button", name="Estrecho").click()
    assert anonymous_page.locator("#mcp-meal-frame").evaluate(
        "element => Math.round(element.getBoundingClientRect().width)"
    ) == 320
    assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")

    anonymous_page.locator("#mcp-meal-scenario").select_option("long")
    expect(card.get_by_role("heading", name="Almuerzo con vegetales, arroz integral y proteína para un día de entrenamiento")).to_be_visible()
    anonymous_page.locator("#mcp-meal-scenario").select_option("empty")
    expect(card.get_by_text("Esta comida no tiene alimentos.")).to_be_visible()
    anonymous_page.locator("#mcp-meal-scenario").select_option("error")
    expect(card.get_by_role("status")).to_contain_text("No se pudo mostrar")
    expect(card.locator("#card")).to_be_hidden()
