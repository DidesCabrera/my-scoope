"""Optional local browser check for the MCP Apps meal card (requires Playwright Chromium)."""

import argparse
import html
from pathlib import Path

from playwright.sync_api import sync_playwright

CARD_PATH = Path(__file__).parent / "myscoope_mcp" / "ui" / "meal_card_v5.html"
SAMPLE_RESULT = {
    "ok": True,
    "data": {
        "meal": {
            "id": 23,
            "name": "Porotos negros con arroz y palta",
            "category": "Almuerzo",
            "kpis": {"total_kcal": 931, "protein": 40, "carbs": 173, "fat": 9.1,
                     "ppk": 0.5, "alloc_protein": 17, "alloc_carbs": 74, "alloc_fat": 9},
            "foods": [
                {"food_name": "Porotos negros cocidos", "quantity": 340,
                 "total_kcal": 459, "protein": 30.1, "carbs": 80.6, "fat": 1.8},
                {"food_name": "Arroz blanco cocido", "quantity": 300,
                 "total_kcal": 378, "protein": 8.1, "carbs": 84.5, "fat": 0.8},
                {"food_name": "Palta", "quantity": 42,
                 "total_kcal": 73, "protein": 0.8, "carbs": 3.6, "fat": 6.2},
                {"food_name": "Tomate", "quantity": 100,
                 "total_kcal": 21, "protein": 0.9, "carbs": 3.9, "fat": 0.2},
            ],
        },
    },
    "error": None,
}


def send_result(page, result):
    page.evaluate(
        """result => document.querySelector("iframe").contentWindow.postMessage({
            jsonrpc: "2.0",
            method: "ui/notifications/tool-result",
            params: {structuredContent: result}
        }, "*")""",
        result,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", type=Path, help="Save a sample card PNG here.")
    parser.add_argument("--screenshot-web", type=Path, help="Save the 760px ChatGPT web layout PNG here.")
    parser.add_argument("--screenshot-panel", type=Path, help="Save the 570px ChatGPT panel layout PNG here.")
    parser.add_argument("--screenshot-mobile", type=Path, help="Save the 320px ChatGPT mobile layout PNG here.")
    args = parser.parse_args()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1160, "height": 900})
        card_html = html.escape(CARD_PATH.read_text(encoding="utf-8"), quote=True)
        page.set_content(f"""
            <script>
              window.bridgeMessages = [];
              window.addEventListener("message", (event) => {{
                if (event.source !== document.querySelector("iframe")?.contentWindow) return;
                const message = event.data;
                window.bridgeMessages.push(message);
                if (message.method === "ui/initialize") {{
                  event.source.postMessage({{
                    jsonrpc: "2.0", id: message.id,
                    result: {{ protocolVersion: "2026-01-26", hostCapabilities: {{}},
                               hostInfo: {{ name: "smoke", version: "1.0.0" }},
                               hostContext: {{ theme: "dark" }} }},
                  }}, "*");
                }}
                if (message.method === "ui/notifications/initialized") window.bridgeReady = true;
              }});
            </script>
            <iframe srcdoc="{card_html}" style="width:1100px;height:800px;border:0"></iframe>
        """)
        page.wait_for_function("window.bridgeReady === true")
        assert page.evaluate("window.bridgeMessages[0].params.protocolVersion") == "2026-01-26"
        card = page.frame_locator("iframe")
        send_result(page, SAMPLE_RESULT)
        card.get_by_role("heading", name="Porotos negros con arroz y palta").wait_for()
        page.wait_for_function("window.bridgeMessages.some(message => message.method === 'ui/notifications/size-changed' && message.params.height > 300)")
        assert card.locator("#meal-kcal").inner_text() == "931"
        assert card.locator(".kcal-box").evaluate(
            "element => Math.abs(element.getBoundingClientRect().width - element.getBoundingClientRect().height) < 1"
        )
        assert card.locator("#meal-protein").inner_text() == "40g"
        assert card.locator("#meal-protein-bar").get_attribute("aria-label") == "17%"
        assert card.locator("#meal-carbs-bar").get_attribute("aria-label") == "74%"
        assert card.locator("#meal-fat-bar").get_attribute("aria-label") == "9%"
        assert card.locator("#meal-food-table tr").count() == 4
        assert card.locator("#meal-food-table tr").nth(2).locator("td").nth(10).get_by_role("img").get_attribute("aria-label") == "68%"
        assert card.locator("#meal-food-table").is_visible()
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            card.locator("#card").screenshot(path=str(args.screenshot))

        page.locator("iframe").evaluate("element => element.style.width = '760px'")
        assert card.locator("#meal-food-table").is_visible()
        assert card.locator("#meal-foods").is_hidden()
        assert card.locator("#meal-food-table tr").first.locator("td").last.evaluate(
            "element => element.getBoundingClientRect().right <= document.querySelector('.food-panel').getBoundingClientRect().right"
        )
        assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")
        if args.screenshot_web:
            args.screenshot_web.parent.mkdir(parents=True, exist_ok=True)
            card.locator("#card").screenshot(path=str(args.screenshot_web))

        page.locator("iframe").evaluate("element => element.style.width = '620px'")
        assert card.locator("#meal-food-table").is_visible()
        assert card.locator(".food-panel").evaluate(
            "element => element.scrollWidth > element.clientWidth || "
            "element.querySelector('tbody tr td:last-child').getBoundingClientRect().right "
            "<= element.getBoundingClientRect().right"
        )

        page.locator("iframe").evaluate("element => element.style.width = '570px'")
        assert card.locator("#meal-food-table").is_visible()
        assert card.locator("#meal-foods").is_hidden()
        assert card.locator(".food-panel").evaluate(
            "element => element.scrollWidth > element.clientWidth || "
            "element.querySelector('tbody tr td:last-child').getBoundingClientRect().right "
            "<= element.getBoundingClientRect().right"
        )
        assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")
        if args.screenshot_panel:
            args.screenshot_panel.parent.mkdir(parents=True, exist_ok=True)
            card.locator("#card").screenshot(path=str(args.screenshot_panel))

        page.locator("iframe").evaluate("element => element.style.width = '390px'")
        assert card.locator("#meal-food-table").is_hidden()
        assert card.locator("#meal-foods li").count() == 4
        card.get_by_role("tab", name="Calorías").click()
        assert card.locator("#card").get_attribute("data-mode") == "calories"
        assert card.locator("#meal-foods li").first.get_by_text("49% de la comida").is_visible()
        card.get_by_role("tab", name="Alloc").click()
        assert card.locator("#meal-foods li").nth(2).get_by_text("68%").is_visible()

        assert card.locator(".macro-row").first.evaluate(
            "element => element.querySelector('.macro-ppk').getBoundingClientRect().right "
            "<= element.querySelector('.alloc-bar').getBoundingClientRect().left"
        )
        assert card.locator(".meal-icon").evaluate("element => element.getBoundingClientRect().width <= 20")
        assert card.locator(".kcal-box").evaluate(
            "element => Math.abs(element.getBoundingClientRect().width - element.getBoundingClientRect().height) < 1"
        )
        assert card.locator(".macro-list").evaluate(
            "element => new Set([...element.querySelectorAll('.macro-row .alloc-bar')].map(bar => Math.round(bar.getBoundingClientRect().left))).size === 1"
        )
        assert card.locator(".top-kpis").evaluate(
            "element => element.querySelector('.kcal-box').getBoundingClientRect().height > element.querySelector('.macro-list').getBoundingClientRect().height"
        )

        hostile = {**SAMPLE_RESULT, "data": {"meal": {
            **SAMPLE_RESULT["data"]["meal"],
            "foods": [{"food_name": '<img src=x onerror=alert(1)>', "quantity": 1}],
        }}}
        send_result(page, hostile)
        card.locator("#meal-foods").get_by_text("<img src=x onerror=alert(1)>").wait_for()
        assert card.locator("#meal-foods img").count() == 0
        assert card.locator("#meal-food-table img").count() == 0

        page.locator("iframe").evaluate("element => element.style.width = '320px'")
        assert card.locator(".kcal-box").evaluate(
            "element => Math.abs(element.getBoundingClientRect().width - element.getBoundingClientRect().height) < 1"
        )
        assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")
        assert card.locator("#card").evaluate(
            "element => getComputedStyle(element).backgroundColor",
        ) == "rgb(18, 18, 18)"
        assert card.locator(".macro-row").first.evaluate(
            "element => element.querySelector('.macro-ppk').getBoundingClientRect().right "
            "<= element.querySelector('.alloc-bar').getBoundingClientRect().left"
        )
        if args.screenshot_mobile:
            send_result(page, SAMPLE_RESULT)
            card.locator("#meal-foods li").first.get_by_text("Porotos negros cocidos").wait_for()
            card.get_by_role("tab", name="Alimentos").click()
            args.screenshot_mobile.parent.mkdir(parents=True, exist_ok=True)
            card.locator("#card").screenshot(path=str(args.screenshot_mobile))

        send_result(page, {"ok": False, "data": {}, "error": {"code": "not_found"}})
        assert card.get_by_role("status").is_visible()
        assert not card.locator("#card").is_visible()
        browser.close()
    print("Meal card browser smoke passed.")


if __name__ == "__main__":
    main()
