"""Local Chromium check of the Food and DailyPlan MCP Apps card."""

import argparse
import html
from copy import deepcopy
from pathlib import Path

from playwright.sync_api import sync_playwright

from mcp_server.dev_meal_card_preview import SAMPLE_DAILYPLAN, SAMPLE_FOOD

CARD_PATH = Path(__file__).parent / "myscoope_mcp" / "ui" / "entity_card_v2.html"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 1000})
        card_source = CARD_PATH.read_text(encoding="utf-8").replace(
            '"__MYSCOOPE_APP_BASE_URL__"', '"https://myscoope-staging.onrender.com/app"'
        )
        card_source = card_source.replace(
            "</head>",
            '<script>window.openai={openExternal: options => window.parent.postMessage({method:"mock/openExternal", options},"*")};</script></head>',
            1,
        )
        card_html = html.escape(card_source, quote=True)
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
            assert card.locator("#detail-link").is_visible() == (kind == "dailyplan")
            if kind == "dailyplan":
                assert card.locator(".badge--meal").evaluate("element => getComputedStyle(element).backgroundColor !== getComputedStyle(document.querySelector('.entity-icon')).backgroundColor")
                assert card.locator(".badge--food").evaluate("element => getComputedStyle(element).backgroundColor !== getComputedStyle(document.querySelector('.badge--meal')).backgroundColor")
                assert card.locator(".badge--meal svg").count() == 1
                assert card.locator(".badge--food svg").count() == 1
                assert card.locator("#detail-link").get_attribute("href") == "https://myscoope-staging.onrender.com/app/dailyplans/42/"
                assert card.locator("#detail-link span").is_visible()
                card.locator("#detail-link").click()
                page.wait_for_function("window.externalOpen?.href === 'https://myscoope-staging.onrender.com/app/dailyplans/42/'")
                assert page.evaluate("window.externalOpen.redirectUrl") is False
                assert card.locator(".detail-row").count() == 3
                assert card.locator(".detail-row .meal-row-icon svg").count() == 3
                assert card.locator("#menu-tab").get_attribute("aria-selected") == "true"
                assert card.locator("#nutrition-panel").is_hidden()
            if args.output_dir:
                args.output_dir.mkdir(parents=True, exist_ok=True)
                card.locator("#card").screenshot(path=str(args.output_dir / f"{kind}-desktop.png"))
            if kind == "dailyplan":
                card.locator("#nutrition-tab").click()
                assert card.locator("#detail-panel").is_hidden()
                assert card.locator("#nutrition-tab").get_attribute("aria-selected") == "true"
                assert card.locator("#nutrition-rows tr").count() == 3
                assert card.locator("#nutrition-rows .meal-row-icon svg").count() == 3
                assert card.locator("#nutrition-rows tr").first.locator("td").first.inner_text() == "Desayuno"
                assert card.locator("#nutrition-rows tr").first.locator("td").nth(1).inner_text() == "447"
                if args.output_dir:
                    card.locator("#card").screenshot(path=str(args.output_dir / "dailyplan-nutrition-desktop.png"))
                card.locator("#menu-tab").focus()
                card.locator("#menu-tab").press("ArrowRight")
                assert card.locator("#nutrition-tab").get_attribute("aria-selected") == "true"
                card.locator("#menu-tab").click()
                assert card.locator("#detail-panel").is_visible()
                card.locator('[data-panel="foods"]').click()
                assert card.locator(".food-panel-desktop button").get_attribute("aria-selected") == "true"
                assert card.locator("#aggregate-food-rows tr").count() == 9
                assert card.locator("#aggregate-food-rows tr").first.locator("td").count() == 11
                card.locator('[data-panel="meals"]').click()
            page.locator("iframe").evaluate("element => element.style.width = '390px'")
            assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")
            assert card.locator(".macro-list").evaluate("element => new Set([...element.querySelectorAll('.macro-row .alloc-bar')].map(bar => Math.round(bar.getBoundingClientRect().left))).size === 1")
            assert card.locator(".kcal-box").evaluate("element => Math.abs(element.getBoundingClientRect().width - element.getBoundingClientRect().height) < 1")
            if args.output_dir:
                card.locator("#card").screenshot(path=str(args.output_dir / f"{kind}-mobile.png"))
            if kind == "dailyplan":
                assert card.locator("#detail-link span").is_hidden()
                assert card.locator("#detail-link").get_attribute("aria-label") == "Ver en My Scoope"
                assert card.locator(".detail-tabs--desktop").is_hidden()
                assert card.locator("#menu-tab-mobile").get_attribute("aria-selected") == "true"
                for mode in ("calories", "macros", "dist", "alloc"):
                    card.locator(f"#{mode}-tab").click()
                    assert card.locator(f"#{mode}-tab").get_attribute("aria-selected") == "true"
                    assert card.locator(f"#{mode}-panel").is_visible()
                    assert card.locator(f"#{mode}-rows .mobile-grid-row").count() == 3
                    assert card.locator("#detail-panel").is_hidden()
                    assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")
                    if args.output_dir:
                        card.locator("#card").screenshot(path=str(args.output_dir / f"dailyplan-{mode}-mobile.png"))
                assert card.locator("#macros-rows .mobile-ppk").first.inner_text() == "0,3"
                assert card.locator("#dist-rows .mobile-dist-protein").first.inner_text() == "24%"
                card.locator("#menu-tab-mobile").click()
                assert card.locator("#detail-panel").is_visible()
                page.locator("iframe").evaluate("element => element.style.width = '320px'")
                card.locator("#alloc-tab").click()
                assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")
                long_plan = deepcopy(SAMPLE_DAILYPLAN)
                long_plan["data"]["dailyplan"]["meals"][0]["meal_name"] = "Yogur con manzana y nueces"
                long_plan["data"]["dailyplan"]["meals"][1]["meal_name"] = "Garbanzos con camote y espinaca"
                page.evaluate("result => document.querySelector('iframe').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:result}},'*')", long_plan)
                card.locator("#macros-tab").click()
                assert card.locator("#macros-rows .mobile-meal-identity strong").first.inner_text() == "Yogur con manzana y nueces"
                assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")
                card.locator('[data-panel="foods"]').click()
                assert card.locator("#food-tab-foods").get_attribute("aria-selected") == "true"
                assert card.locator("#food-tab-foods").inner_text() == "Tabla Alimentos"
                card.locator('#food-tab-alloc').click()
                assert card.locator("#food-panel-alloc .mobile-grid-row").count() == 9
                assert card.locator("#macros-tab").get_attribute("aria-selected") == "true"
                assert card.locator("html").evaluate("element => element.scrollWidth <= innerWidth")
                if args.output_dir:
                    card.locator("#card").screenshot(path=str(args.output_dir / "dailyplan-long-names-mobile.png"))
        millilitre_food = {**SAMPLE_FOOD, "data": {"food": {**SAMPLE_FOOD["data"]["food"], "portion_unit": "ml"}}}
        page.evaluate("result => document.querySelector('iframe').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:result}},'*')", millilitre_food)
        card.locator("#badges").get_by_text("Por 100 ml").wait_for()
        hostile = {**SAMPLE_FOOD, "data": {"food": {**SAMPLE_FOOD["data"]["food"], "name": "<img src=x onerror=alert(1)>"}}}
        page.evaluate("result => document.querySelector('iframe').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:result}},'*')", hostile)
        card.locator("#entity-name").get_by_text("<img src=x onerror=alert(1)>").wait_for()
        assert card.locator("#card img:visible").count() == 0
        page.evaluate("document.querySelector('iframe').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:{ok:false,data:{},error:{code:'not_found'}}}},'*')")
        assert card.locator("#card").is_hidden()
        assert card.locator("#status").is_visible()
        browser.close()
    print("Food and DailyPlan card browser smoke passed.")


if __name__ == "__main__":
    main()
