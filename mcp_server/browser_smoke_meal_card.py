"""Optional local browser check for the MCP Apps meal card (requires Playwright Chromium)."""

import argparse
import html
from pathlib import Path

from playwright.sync_api import sync_playwright


CARD_PATH = Path(__file__).parent / "myscoope_mcp" / "ui" / "meal_card_v2.html"
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
    args = parser.parse_args()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 520, "height": 480})
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
                               hostInfo: {{ name: "smoke", version: "1.0.0" }}, hostContext: {{}} }},
                  }}, "*");
                }}
                if (message.method === "ui/notifications/initialized") window.bridgeReady = true;
              }});
            </script>
            <iframe srcdoc="{card_html}" style="width:100%;height:480px;border:0"></iframe>
        """)
        page.wait_for_function("window.bridgeReady === true")
        assert page.evaluate("window.bridgeMessages[0].params.protocolVersion") == "2026-01-26"
        card = page.frame_locator("iframe")
        send_result(page, SAMPLE_RESULT)
        card.get_by_role("heading", name="Almuerzo de prueba").wait_for()
        page.wait_for_function("window.bridgeMessages.some(message => message.method === 'ui/notifications/size-changed')")
        assert card.locator("#meal-kcal").inner_text() == "614"
        assert card.locator("#meal-protein").inner_text() == "35,5 g"
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            card.locator("#card").screenshot(path=str(args.screenshot))

        card.get_by_role("tab", name="Alimentos").click()
        assert card.locator("#meal-foods li").count() == 2
        assert card.locator("#panel-foods").is_visible()
        assert not card.locator("#panel-summary").is_visible()

        hostile = {**SAMPLE_RESULT, "data": {"meal": {
            **SAMPLE_RESULT["data"]["meal"],
            "foods": [{"food_name": '<img src=x onerror=alert(1)>', "quantity": 1}],
        }}}
        send_result(page, hostile)
        card.get_by_role("tab", name="Alimentos").click()
        card.locator("#meal-foods").get_by_text("<img src=x onerror=alert(1)>").wait_for()
        assert card.locator("#meal-foods img").count() == 0
        assert "<img src=x onerror=alert(1)>" in card.locator("#meal-foods").inner_text()

        page.set_viewport_size({"width": 320, "height": 480})
        assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")
        page.emulate_media(color_scheme="dark")
        assert card.locator("#card").evaluate(
            "element => getComputedStyle(element).backgroundColor",
        ) == "rgb(36, 26, 42)"

        send_result(page, {"ok": False, "data": {}, "error": {"code": "not_found"}})
        assert card.get_by_role("status").is_visible()
        assert not card.locator("#card").is_visible()
        browser.close()
    print("Meal card browser smoke passed.")


if __name__ == "__main__":
    main()
