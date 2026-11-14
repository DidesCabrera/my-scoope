"""Optional local browser check for the MCP Apps meal card (requires Playwright Chromium)."""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


CARD_PATH = Path(__file__).parent / "myscoope_mcp" / "ui" / "meal_card_v1.html"
SAMPLE_RESULT = {
    "ok": True,
    "data": {
        "meal": {
            "id": 23,
            "name": "Almuerzo de prueba",
            "category": "Almuerzo",
            "kpis": {"total_kcal": 614.4, "protein": 35.5, "carbs": 74.2, "fat": 19.1},
            "foods": [
                {"food_name": "Arroz integral", "quantity": 180},
                {"food_name": "Pollo a la plancha", "quantity": 120},
            ],
        },
    },
    "error": None,
}


def send_result(page, result):
    page.evaluate(
        """result => window.postMessage({
            jsonrpc: "2.0",
            method: "ui/notifications/tool-result",
            params: {structuredContent: result}
        }, "*")""",
        result,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", type=Path, help="Save a sample card PNG here.")
    args = parser.parse_args()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 520, "height": 480})
        page.goto(CARD_PATH.resolve().as_uri())
        send_result(page, SAMPLE_RESULT)
        page.get_by_role("heading", name="Almuerzo de prueba").wait_for()
        assert page.locator("#meal-kcal").inner_text() == "614"
        assert page.locator("#meal-protein").inner_text() == "35,5 g"
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.locator("#card").screenshot(path=str(args.screenshot))

        page.get_by_role("tab", name="Alimentos").click()
        assert page.locator("#meal-foods li").count() == 2
        assert page.locator("#panel-foods").is_visible()
        assert not page.locator("#panel-summary").is_visible()

        hostile = {**SAMPLE_RESULT, "data": {"meal": {
            **SAMPLE_RESULT["data"]["meal"],
            "foods": [{"food_name": '<img src=x onerror=alert(1)>', "quantity": 1}],
        }}}
        send_result(page, hostile)
        page.wait_for_function(
            "() => document.querySelector('#meal-foods').textContent.includes('<img src=x')",
        )
        assert page.locator("#meal-foods img").count() == 0
        assert "<img src=x onerror=alert(1)>" in page.locator("#meal-foods").inner_text()

        page.set_viewport_size({"width": 320, "height": 480})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.emulate_media(color_scheme="dark")
        assert page.locator("#card").evaluate(
            "element => getComputedStyle(element).backgroundColor",
        ) == "rgb(36, 26, 42)"

        send_result(page, {"ok": False, "data": {}, "error": {"code": "not_found"}})
        assert page.get_by_role("status").is_visible()
        assert not page.locator("#card").is_visible()
        browser.close()
    print("Meal card browser smoke passed.")


if __name__ == "__main__":
    main()
