"""Local Chromium check of the composed MCP proposal card."""

import argparse
import html
from pathlib import Path

from playwright.sync_api import sync_playwright

from mcp_server.dev_meal_card_preview import SAMPLE_PROPOSAL

CARD_PATH = Path(__file__).parent / "myscoope_mcp" / "ui" / "proposal_card_v1.html"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    source = CARD_PATH.read_text(encoding="utf-8").replace(
        '"__MYSCOOPE_APP_BASE_URL__"', '"https://myscoope-staging.onrender.com/app"'
    )
    source = source.replace(
        "</head>",
        '<script>window.openai={openExternal: options => window.parent.postMessage({method:"mock/openExternal", options},"*")};</script></head>',
        1,
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 1000})
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
              if (event.data.method === "mock/openExternal") window.externalOpen = event.data.options;
            }});
          </script>
          <iframe srcdoc="{html.escape(source, quote=True)}" style="width:1100px;height:900px;border:0"></iframe>
        """)
        page.wait_for_function("window.bridgeReady")
        page.evaluate("result => document.querySelector('iframe').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:result}},'*')", SAMPLE_PROPOSAL)
        card = page.frame_locator("iframe")
        card.locator("#proposal-shell").wait_for(state="visible")
        assert card.locator("#card").get_attribute("data-entity") == "dailyplan"
        assert card.locator(".detail-row").count() == 4
        assert card.locator("#proposal-title").inner_text() == "Minuta diaria para revisión"
        assert card.locator("#proposal-status").inner_text() == "Pendiente de revisión"
        assert card.locator("#detail-link").is_hidden()
        assert card.locator("#proposal-link").get_attribute("href") == "https://myscoope-staging.onrender.com/app/proposals/26/"
        assert card.locator("#proposal-shell").evaluate("element => getComputedStyle(element).borderTopColor === getComputedStyle(element).borderLeftColor")
        if args.output_dir:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            card.locator("#proposal-shell").screenshot(path=str(args.output_dir / "proposal-desktop.png"))
        card.locator("#nutrition-tab").click()
        assert card.locator("#nutrition-rows tr").count() == 4
        card.locator("#proposal-link").click()
        page.wait_for_function("window.externalOpen?.href === 'https://myscoope-staging.onrender.com/app/proposals/26/'")
        for width in (390, 320):
            page.locator("iframe").evaluate(f"element => element.style.width = '{width}px'")
            assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")
            card.locator("#menu-tab-mobile").click()
            assert card.locator(".detail-row").count() == 4
            if args.output_dir:
                card.locator("#proposal-shell").screenshot(path=str(args.output_dir / f"proposal-{width}px.png"))
            card.locator("#macros-tab").click()
            assert card.locator("#macros-rows .mobile-grid-row").count() == 4
            assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")
        browser.close()
    print("Proposal card browser smoke passed.")


if __name__ == "__main__":
    main()
