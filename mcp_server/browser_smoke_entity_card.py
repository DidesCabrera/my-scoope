"""Local Chromium check of the Food and DailyPlan MCP Apps card."""

import argparse
import html
from pathlib import Path

from playwright.sync_api import sync_playwright

from mcp_server.dev_meal_card_preview import SAMPLE_DAILYPLAN, SAMPLE_FOOD

CARD_PATH = Path(__file__).parent / "myscoope_mcp" / "ui" / "entity_card_v1.html"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 1000})
        card_html = html.escape(CARD_PATH.read_text(encoding="utf-8"), quote=True)
        page.set_content(f"""
          <script>
            window.bridgeReady = false;
            window.addEventListener("message", event => {{
              if (event.source !== document.querySelector("iframe")?.contentWindow) return;
              if (event.data.method === "ui/initialize") event.source.postMessage({{
                jsonrpc: "2.0", id: event.data.id,
                result: {{protocolVersion: "2026-01-26", hostCapabilities: {{}},
                  hostInfo: {{name: "smoke", version: "1.0"}}, hostContext: {{theme: "dark"}}}}
              }}, "*");
              if (event.data.method === "ui/notifications/initialized") window.bridgeReady = true;
            }});
          </script>
          <iframe srcdoc="{card_html}" style="width:1100px;height:850px;border:0"></iframe>
        """)
        page.wait_for_function("window.bridgeReady")
        card = page.frame_locator("iframe")
        for kind, result in (("food", SAMPLE_FOOD), ("dailyplan", SAMPLE_DAILYPLAN)):
            page.locator("iframe").evaluate("element => element.style.width = '1100px'")
            page.evaluate("result => document.querySelector('iframe').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:result}},'*')", result)
            card.locator("#card").wait_for(state="visible")
            assert card.locator("#card").get_attribute("data-entity") == kind
            assert card.locator("#total-kcal").inner_text() == ("382" if kind == "food" else "1.950")
            assert card.locator(".macro-row").count() == 3
            assert card.locator(".kcal-box").evaluate("element => Math.abs(element.getBoundingClientRect().width - element.getBoundingClientRect().height) < 1")
            assert card.locator("#detail").is_visible() == (kind == "dailyplan")
            if kind == "dailyplan":
                assert card.locator(".detail-row").count() == 3
            if args.output_dir:
                args.output_dir.mkdir(parents=True, exist_ok=True)
                card.locator("#card").screenshot(path=str(args.output_dir / f"{kind}-desktop.png"))
            page.locator("iframe").evaluate("element => element.style.width = '320px'")
            assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")
            assert card.locator(".macro-list").evaluate("element => new Set([...element.querySelectorAll('.macro-row .alloc-bar')].map(bar => Math.round(bar.getBoundingClientRect().left))).size === 1")
            assert card.locator(".kcal-box").evaluate("element => Math.abs(element.getBoundingClientRect().width - element.getBoundingClientRect().height) < 1")
            if args.output_dir:
                card.locator("#card").screenshot(path=str(args.output_dir / f"{kind}-mobile.png"))
        millilitre_food = {**SAMPLE_FOOD, "data": {"food": {**SAMPLE_FOOD["data"]["food"], "portion_unit": "ml"}}}
        page.evaluate("result => document.querySelector('iframe').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:result}},'*')", millilitre_food)
        card.locator("#badges").get_by_text("Por 100 ml").wait_for()
        hostile = {**SAMPLE_FOOD, "data": {"food": {**SAMPLE_FOOD["data"]["food"], "name": "<img src=x onerror=alert(1)>"}}}
        page.evaluate("result => document.querySelector('iframe').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:result}},'*')", hostile)
        card.locator("#entity-name").get_by_text("<img src=x onerror=alert(1)>").wait_for()
        assert card.locator("#card img").count() == 0
        page.evaluate("document.querySelector('iframe').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:{ok:false,data:{},error:{code:'not_found'}}}},'*')")
        assert card.locator("#card").is_hidden()
        assert card.locator("#status").is_visible()
        browser.close()
    print("Food and DailyPlan card browser smoke passed.")


if __name__ == "__main__":
    main()
