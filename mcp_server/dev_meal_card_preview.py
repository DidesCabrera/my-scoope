"""Synthetic, local-only MCP Apps host for fast meal-card CSS iteration.

Expose this process to ChatGPT only through a private development tunnel. It has
no My Scoope API access and serves no account data.
"""

import argparse
import re
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP


UI_DIR = Path(__file__).parent / "myscoope_mcp" / "ui"
CARD_PATH = UI_DIR / "meal_card_v5.html"
SOURCE_PATH = UI_DIR / "meal_card_v5.source.html"
ENTITY_CARD_PATH = UI_DIR / "entity_card_v1.html"
ENTITY_SOURCE_PATH = UI_DIR / "entity_card_v1.source.html"
MIME_TYPE = "text/html;profile=mcp-app"
STYLE_PATTERN = re.compile(r"<style>(.*?)</style>", re.DOTALL)

SAMPLE_MEAL = {
    "ok": True,
    "data": {"meal": {
        "id": 0,
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
    }},
    "error": None,
}



SAMPLE_FOOD = {
    "ok": True,
    "data": {"food": {
        "id": 0, "name": "Avena tradicional", "category": "Cereal", "portion_unit": "g",
        "macros": {"total_kcal": 382, "protein": 13, "carbs": 67, "fat": 7,
                   "alloc_protein": 14, "alloc_carbs": 70, "alloc_fat": 16},
    }},
    "error": None,
}

SAMPLE_DAILYPLAN = {
    "ok": True,
    "data": {"dailyplan": {
        "id": 0, "name": "Minuta de un día equilibrado", "category": "Diaria",
        "meals_count": 3, "foods_count": 9,
        "kpis": {"total_kcal": 1950, "protein": 120, "carbs": 225, "fat": 63,
                 "ppk": 1.5, "alloc_protein": 25, "alloc_carbs": 46, "alloc_fat": 29},
        "meals": [
            {"meal_name": "Desayuno", "hour": "08:00", "kpis": {"total_kcal": 447, "ppk": 0.3, "protein": 27, "carbs": 75, "fat": 5,
                      "alloc_protein": 24, "alloc_carbs": 67, "alloc_fat": 9},
             "foods": [{"food_name": "Avena tradicional"}, {"food_name": "Yogur natural"}, {"food_name": "Plátano"}]},
            {"meal_name": "Almuerzo", "hour": "13:30", "kpis": {"total_kcal": 931, "ppk": 0.6, "protein": 50, "carbs": 100, "fat": 37,
                      "alloc_protein": 21, "alloc_carbs": 43, "alloc_fat": 36},
             "foods": [{"food_name": "Porotos negros"}, {"food_name": "Arroz blanco"}, {"food_name": "Palta"}, {"food_name": "Tomate"}]},
            {"meal_name": "Cena", "hour": "20:00", "kpis": {"total_kcal": 572, "ppk": 0.5, "protein": 43, "carbs": 50, "fat": 21,
                      "alloc_protein": 31, "alloc_carbs": 36, "alloc_fat": 33},
             "foods": [{"food_name": "Salmón"}, {"food_name": "Papas cocidas"}]},
        ],
    }},
    "error": None,
}

def current_css(card: str = "meal") -> str:
    source = SOURCE_PATH if card == "meal" else ENTITY_SOURCE_PATH
    match = STYLE_PATTERN.search(source.read_text(encoding="utf-8"))
    if not match:
        raise ValueError("Meal card source has no style block")
    return match.group(1)


def preview_html(card: str = "meal") -> str:
    html = (CARD_PATH if card == "meal" else ENTITY_CARD_PATH).read_text(encoding="utf-8")
    live_script = """
<script>
(() => {
  let requestId = 1000;
  let lastCss = null;
  function refreshStyles() {
    window.parent.postMessage({
      jsonrpc: "2.0", id: ++requestId, method: "tools/call",
      params: {name: "preview_card_styles", arguments: {card: "__CARD__"}}
    }, "*");
  }
  window.addEventListener("message", event => {
    if (event.source !== window.parent || event.data?.jsonrpc !== "2.0") return;
    const message = event.data;
    if (message.id === 1 && message.result?.protocolVersion) {
      refreshStyles();
      setInterval(refreshStyles, 1500);
    }
    if (message.id < 1001 || !message.result) return;
    const css = message.result.structuredContent?.css;
    if (typeof css !== "string" || css === lastCss) return;
    lastCss = css;
    let style = document.getElementById("myscoope-live-css");
    if (!style) {
      style = document.createElement("style");
      style.id = "myscoope-live-css";
      document.head.append(style);
    }
    style.textContent = css;
  });
})();
</script>
"""
    if "</body>" not in html:
        raise ValueError("Card HTML has no body closing tag")
    return html.replace("</body>", live_script.replace("__CARD__", card) + "</body>", 1)


def create_preview_server() -> FastMCP:
    # A new URI per process avoids a stale cached resource when HTML changes.
    version = uuid.uuid4().hex
    uri = f"ui://myscoope-dev/meal-card-{version}.html"
    entity_uri = f"ui://myscoope-dev/entity-card-{version}.html"
    server = FastMCP("My Scoope meal card preview", stateless_http=True)

    @server.tool(
        name="preview_meal_card",
        description="Show a synthetic My Scoope meal for visual preview.",
        meta={"ui": {"resourceUri": uri}},
        structured_output=True,
    )
    def preview_meal_card() -> dict[str, Any]:
        return SAMPLE_MEAL

    @server.tool(
        name="preview_food_card",
        description="Show a synthetic My Scoope food for visual preview.",
        meta={"ui": {"resourceUri": entity_uri}},
        structured_output=True,
    )
    def preview_food_card() -> dict[str, Any]:
        return SAMPLE_FOOD

    @server.tool(
        name="preview_dailyplan_card",
        description="Show a synthetic My Scoope daily plan for visual preview.",
        meta={"ui": {"resourceUri": entity_uri}},
        structured_output=True,
    )
    def preview_dailyplan_card() -> dict[str, Any]:
        return SAMPLE_DAILYPLAN

    @server.tool(
        name="preview_card_styles",
        description="Read local card CSS for the preview iframe.",
        meta={"ui": {"visibility": ["app"]}},
        structured_output=True,
    )
    def preview_card_styles(card: str = "meal") -> dict[str, str]:
        return {"css": current_css(card)}

    @server.resource(uri, name="My Scoope meal card development preview", mime_type=MIME_TYPE)
    def card_resource() -> str:
        return preview_html()

    @server.resource(entity_uri, name="My Scoope entity card development preview", mime_type=MIME_TYPE)
    def entity_resource() -> str:
        return preview_html("entity")

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()
    server = create_preview_server()
    uvicorn.run(server.streamable_http_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
