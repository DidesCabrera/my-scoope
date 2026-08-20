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
