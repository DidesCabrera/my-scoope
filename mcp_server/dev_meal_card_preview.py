"""Synthetic, local-only MCP Apps host for fast meal-card CSS iteration.

Expose this process to ChatGPT only through a private development tunnel. It has
no My Scoope API access and serves no account data.
"""

import argparse
import logging
import re
from pathlib import Path
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP

UI_DIR = Path(__file__).parent / "myscoope_mcp" / "ui"
CARD_PATH = UI_DIR / "meal_card_v8.html"
SOURCE_PATH = UI_DIR / "meal_card_v8.source.html"
ENTITY_CARD_PATH = UI_DIR / "entity_card_v1.html"
ENTITY_SOURCE_PATH = UI_DIR / "entity_card_v1.source.html"
DAILYPLAN_CARD_PATH = UI_DIR / "entity_card_v2.html"
DAILYPLAN_SOURCE_PATH = UI_DIR / "entity_card_v2.source.html"
PROPOSAL_CARD_PATH = UI_DIR / "proposal_card_v1.html"
PROPOSAL_CSS_PATH = UI_DIR / "proposal_card_v1.css"
MIME_TYPE = "text/html;profile=mcp-app"
STYLE_PATTERN = re.compile(r"<style>(.*?)</style>", re.DOTALL)
LEGACY_VERSION_PATTERN = re.compile(r"[0-9a-f]{32}")
MEAL_CARD_URI = "ui://myscoope-dev/meal-card-v8.html"
RECENT_MEAL_CARD_URI = "ui://myscoope-dev/meal-card-v7.html"
PREVIOUS_MEAL_CARD_URI = "ui://myscoope-dev/meal-card-v6.html"
ENTITY_CARD_URI = "ui://myscoope-dev/entity-card-v1.html"
DAILYPLAN_CARD_URI = "ui://myscoope-dev/dailyplan-card-v2.html"
PROPOSAL_CARD_URI = "ui://myscoope-dev/proposal-card-v1.html"
PROBE_CARD_URI = "ui://myscoope-dev/probe-card-v1.html"
logger = logging.getLogger(__name__)


class PreviewFastMCP(FastMCP):
    async def read_resource(self, uri: Any) -> Any:
        try:
            result = await super().read_resource(uri)
        except Exception as exc:
            logger.warning("Preview UI resource read failed: %s (%s)", uri, exc)
            raise
        logger.info("Preview UI resource read succeeded: %s", uri)
        return result

SAMPLE_MEAL = {
    "ok": True,
    "data": {"meal": {
        "id": 0,
        "name": "Pollo con arroz integral y ensalada",
        "category": "Almuerzo",
        "kpis": {"total_kcal": 726, "protein": 70, "carbs": 70, "fat": 19,
                 "ppk": 1, "alloc_protein": 38, "alloc_carbs": 39, "alloc_fat": 23},
        "foods": [
            {"food_name": "Pechuga de pollo cocida", "quantity": 200, "quantity_unit": "g", "ppk": 0.9, "emoji": "🍗",
             "image_path": "/api/v1/foods/visual-assets/07ee5a6a-7dda-4951-bfc6-9c002efbe231/f25f69beb536c303385dc692860e97cbcb553d05dd1710f2cc525f64c76c40a9.png",
             "total_kcal": 311, "protein": 62, "carbs": 0, "fat": 7},
            {"food_name": "Arroz integral cocido", "quantity": 250, "quantity_unit": "g", "ppk": 0.1, "emoji": "🍚",
             "image_path": "/api/v1/foods/visual-assets/4fac0ec0-92a4-461e-8c37-4259d25b332e/2ce057b0cc43f17dd6960e76bc311d1d7b757b742d2ae4ee84afbbc7b1374def.png",
             "total_kcal": 310, "protein": 7, "carbs": 67, "fat": 2},
            {"food_name": "Lechuga costina cruda", "quantity": 100, "quantity_unit": "g", "ppk": 0, "emoji": "🥬",
             "image_path": "/api/v1/foods/visual-assets/bd300a6f-ae37-435d-89b5-89e8fae975dd/65071b7c8ed1a736d19d975772762b43709adf23ada6a5c1c379ae8e378cb720.png",
             "total_kcal": 15, "protein": 1, "carbs": 3, "fat": 0},
            {"food_name": "Aceite de oliva", "quantity": 10, "quantity_unit": "g", "ppk": 0, "emoji": "🫒",
             "image_path": "/api/v1/foods/visual-assets/0481f062-c35f-4156-8e38-8f093caedfcc/26f746387eafc47291de70cfb5d1ac25544a0d6d57b6b3b78e558ac2b461f1ba.png",
             "total_kcal": 90, "protein": 0, "carbs": 0, "fat": 10},
        ],
    }},
    "error": None,
}



SAMPLE_FOOD = {
    "ok": True,
    "data": {"food": {
        "id": 0, "name": "Avena tradicional", "category": "Cereal", "portion_unit": "g",
        "image_path": "/api/v1/foods/visual-assets/aeba4865-b1ae-4f58-b1e8-2b0e250b08bf/8f36fb066a3c2b6d10ea6ade41890e6668646b9811af068faf3957cb7e697e06.png",
        "macros": {"total_kcal": 382, "protein": 13, "carbs": 67, "fat": 7,
                   "alloc_protein": 14, "alloc_carbs": 70, "alloc_fat": 16},
    }},
    "error": None,
}

PREVIEW_FOOD_IMAGES = {
    "Avena tradicional": SAMPLE_FOOD["data"]["food"]["image_path"],
    "Pechuga de pollo": SAMPLE_MEAL["data"]["meal"]["foods"][0]["image_path"],
    "Arroz integral": SAMPLE_MEAL["data"]["meal"]["foods"][1]["image_path"],
    "Lechuga": SAMPLE_MEAL["data"]["meal"]["foods"][2]["image_path"],
    "Aceite de oliva": SAMPLE_MEAL["data"]["meal"]["foods"][3]["image_path"],
}


def _preview_food(name: str) -> dict:
    item = {"food_name": name}
    if image_path := PREVIEW_FOOD_IMAGES.get(name):
        item["image_path"] = image_path
    return item

SAMPLE_DAILYPLAN = {
    "ok": True,
    "data": {"dailyplan": {
        "id": 42, "name": "Minuta de un día equilibrado", "category": "Diaria",
        "meals_count": 3, "foods_count": 9,
        "kpis": {"total_kcal": 1950, "protein": 120, "carbs": 225, "fat": 63,
                 "ppk": 1.5, "alloc_protein": 25, "alloc_carbs": 46, "alloc_fat": 29},
        "meals": [
            {"meal_name": "Desayuno", "hour": "08:00", "kpis": {"total_kcal": 447, "ppk": 0.3, "protein": 27, "carbs": 75, "fat": 5,
                      "alloc_protein": 24, "alloc_carbs": 67, "alloc_fat": 9},
             "foods": [{**_preview_food("Avena tradicional"), "quantity": 80, "quantity_unit": "g"}, {"food_name": "Yogur natural", "quantity": 180, "quantity_unit": "g"}, {"food_name": "Plátano", "quantity": 120, "quantity_unit": "g"}]},
            {"meal_name": "Almuerzo", "hour": "13:30", "kpis": {"total_kcal": 931, "ppk": 0.6, "protein": 50, "carbs": 100, "fat": 37,
                      "alloc_protein": 21, "alloc_carbs": 43, "alloc_fat": 36},
             "foods": [{"food_name": "Porotos negros", "quantity": 340, "quantity_unit": "g"}, {"food_name": "Arroz blanco", "quantity": 300, "quantity_unit": "g"}, {"food_name": "Palta", "quantity": 42, "quantity_unit": "g"}, {"food_name": "Tomate", "quantity": 100, "quantity_unit": "g"}]},
            {"meal_name": "Cena", "hour": "20:00", "kpis": {"total_kcal": 572, "ppk": 0.5, "protein": 43, "carbs": 50, "fat": 21,
                      "alloc_protein": 31, "alloc_carbs": 36, "alloc_fat": 33},
             "foods": [{"food_name": "Salmón", "quantity": 180, "quantity_unit": "g"}, {"food_name": "Papas cocidas", "quantity": 250, "quantity_unit": "g"}]},
        ],
    }},
    "error": None,
}

SAMPLE_PROPOSAL_DAILYPLAN = {
    "id": 0,
    "name": "Día de mantenimiento",
    "category": "Diaria",
    "meals_count": 4,
    "foods_count": 15,
    "kpis": {"total_kcal": 1947, "protein": 120, "carbs": 225, "fat": 63,
             "ppk": 1.7, "alloc_protein": 25, "alloc_carbs": 46, "alloc_fat": 29},
    "meals": [
        {"meal_name": "Avena con yogur y fruta", "hour": "08:00",
         "kpis": {"total_kcal": 448, "protein": 25, "carbs": 60, "fat": 12,
                  "ppk": 0.4, "alloc_protein": 22, "alloc_carbs": 54, "alloc_fat": 24},
         "foods": [_preview_food(name) for name in (
             "Avena tradicional", "Yogur natural", "Plátano", "Nueces")]},
        {"meal_name": "Pollo con arroz y ensalada", "hour": "13:00",
         "kpis": {"total_kcal": 640, "protein": 40, "carbs": 75, "fat": 20,
                  "ppk": 0.6, "alloc_protein": 25, "alloc_carbs": 47, "alloc_fat": 28},
         "foods": [_preview_food(name) for name in (
             "Pechuga de pollo", "Arroz integral", "Tomate", "Lechuga", "Aceite de oliva")]},
        {"meal_name": "Marraqueta con palta y huevo", "hour": "17:00",
         "kpis": {"total_kcal": 310, "protein": 20, "carbs": 35, "fat": 10,
                  "ppk": 0.3, "alloc_protein": 26, "alloc_carbs": 45, "alloc_fat": 29},
         "foods": [_preview_food(name) for name in ("Marraqueta", "Palta", "Huevo cocido")]},
        {"meal_name": "Atún con papas y verduras", "hour": "21:00",
         "kpis": {"total_kcal": 549, "protein": 35, "carbs": 55, "fat": 21,
                  "ppk": 0.5, "alloc_protein": 26, "alloc_carbs": 40, "alloc_fat": 34},
         "foods": [_preview_food(name) for name in ("Atún en agua", "Papa cocida", "Zanahoria")]},
    ],
}

SAMPLE_PROPOSAL = {
    "ok": True,
    "data": {
        "proposal_id": 26,
        "status": "pending_review",
        "requires_human_review": True,
        "applies_changes": False,
        "proposal_card": {
            "id": 26,
            "title": "Minuta diaria para revisión",
            "status": "pending_review",
            "status_label": "Pendiente de revisión",
            "summary": "Revisa las comidas y los valores nutricionales antes de aprobar en My Scoope.",
        },
        "dailyplan": SAMPLE_PROPOSAL_DAILYPLAN,
    },
    "error": None,
}

def current_css(card: str = "meal") -> str:
    source = SOURCE_PATH if card == "meal" else DAILYPLAN_SOURCE_PATH if card in {"dailyplan", "proposal"} else ENTITY_SOURCE_PATH
    match = STYLE_PATTERN.search(source.read_text(encoding="utf-8"))
    if not match:
        raise ValueError("Meal card source has no style block")
    css = match.group(1)
    return css + PROPOSAL_CSS_PATH.read_text(encoding="utf-8") if card == "proposal" else css


def preview_html(card: str = "meal") -> str:
    path = CARD_PATH if card == "meal" else PROPOSAL_CARD_PATH if card == "proposal" else DAILYPLAN_CARD_PATH if card == "dailyplan" else ENTITY_CARD_PATH
    html = path.read_text(encoding="utf-8")
    if card in {"dailyplan", "proposal"}:
        html = html.replace('"__MYSCOOPE_APP_BASE_URL__"', '"http://127.0.0.1:8000/app"')
    if card in {"entity", "dailyplan", "proposal"}:
        html = html.replace('"__MYSCOOPE_IMAGE_ORIGIN__"', '"https://www.myscoope.com"')
    if card == "meal":
        html = html.replace('"__MYSCOOPE_APP_LINK_ORIGIN__"', '"https://www.myscoope.com"')
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
    # Stable URIs survive restarts. Legacy templates keep previously advertised
    # random URIs readable in conversations whose tool metadata is cached.
    uri = MEAL_CARD_URI
    entity_uri = ENTITY_CARD_URI
    dailyplan_uri = DAILYPLAN_CARD_URI
    proposal_uri = PROPOSAL_CARD_URI
    probe_uri = PROBE_CARD_URI
    server = PreviewFastMCP("My Scoope meal card preview", stateless_http=True, json_response=True)

    @server.tool(
        name="preview_meal_card",
        description="Show a synthetic My Scoope meal for visual preview.",
        meta={"ui": {"resourceUri": uri}, "openai/outputTemplate": uri},
        structured_output=True,
    )
    def preview_meal_card() -> dict[str, Any]:
        return SAMPLE_MEAL

    @server.tool(
        name="preview_food_card",
        description="Show a synthetic My Scoope food for visual preview.",
        meta={"ui": {"resourceUri": entity_uri}, "openai/outputTemplate": entity_uri},
        structured_output=True,
    )
    def preview_food_card() -> dict[str, Any]:
        return SAMPLE_FOOD

    @server.tool(
        name="preview_dailyplan_card",
        description="Show a synthetic My Scoope daily plan for visual preview.",
        meta={"ui": {"resourceUri": dailyplan_uri}, "openai/outputTemplate": dailyplan_uri},
        structured_output=True,
    )
    def preview_dailyplan_card() -> dict[str, Any]:
        return SAMPLE_DAILYPLAN

    @server.tool(
        name="preview_proposal_card",
        description="Show a synthetic reviewable DailyPlan proposal with its existing My Scoope card.",
        meta={"ui": {"resourceUri": proposal_uri}, "openai/outputTemplate": proposal_uri},
        structured_output=True,
    )
    def preview_proposal_card() -> dict[str, Any]:
        return SAMPLE_PROPOSAL

    @server.tool(
        name="preview_minimal_card",
        description="Show a minimal synthetic card to diagnose whether this ChatGPT client loads MCP UI resources.",
        meta={"ui": {"resourceUri": probe_uri}, "openai/outputTemplate": probe_uri},
        structured_output=True,
    )
    def preview_minimal_card() -> dict[str, Any]:
        return {"ok": True, "data": {"message": "Vista mínima MCP"}, "error": None}

    @server.tool(
        name="preview_minimal_card_v2",
        description="Show the second minimal MCP UI probe with a fresh tool identity to diagnose mobile resource caching.",
        meta={"ui": {"resourceUri": probe_uri}, "openai/outputTemplate": probe_uri},
        structured_output=True,
    )
    def preview_minimal_card_v2() -> dict[str, Any]:
        return {"ok": True, "data": {"message": "Vista mínima MCP v2"}, "error": None}

    @server.tool(
        name="preview_card_styles",
        description="Read local card CSS for the preview iframe.",
        meta={"ui": {"visibility": ["app"]}},
        structured_output=True,
    )
    def preview_card_styles(card: str = "meal") -> dict[str, str]:
        return {"css": current_css(card)}

    @server.resource(uri, name="My Scoope meal card development preview", mime_type=MIME_TYPE,
                     meta={"openai/widgetCSP": {"resource_domains": ["https://www.myscoope.com"]}})
    def card_resource() -> str:
        return preview_html()

    @server.resource(RECENT_MEAL_CARD_URI, name="Meal card v7 development preview", mime_type=MIME_TYPE)
    def recent_card_resource() -> str:
        return (UI_DIR / "meal_card_v7.html").read_text(encoding="utf-8")

    @server.resource(PREVIOUS_MEAL_CARD_URI, name="Previous meal card development preview", mime_type=MIME_TYPE)
    def previous_card_resource() -> str:
        return (UI_DIR / "meal_card_v6.html").read_text(encoding="utf-8")

    @server.resource(entity_uri, name="My Scoope entity card development preview", mime_type=MIME_TYPE,
                     meta={"openai/widgetCSP": {"resource_domains": ["https://www.myscoope.com"]}})
    def entity_resource() -> str:
        return preview_html("entity")

    @server.resource(dailyplan_uri, name="My Scoope daily plan card development preview", mime_type=MIME_TYPE)
    def dailyplan_resource() -> str:
        return preview_html("dailyplan")

    @server.resource(proposal_uri, name="My Scoope proposal card development preview", mime_type=MIME_TYPE)
    def proposal_resource() -> str:
        return preview_html("proposal")

    @server.resource(probe_uri, name="My Scoope minimal UI diagnostic", mime_type=MIME_TYPE)
    def probe_resource() -> str:
        return """<!doctype html><html lang="es"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body style="margin:0;background:#c523a7;color:white;font:20px system-ui;padding:24px">Vista mínima MCP visible<script>
window.addEventListener("message", (event) => {
  if (event.source !== window.parent || event.data?.jsonrpc !== "2.0") return;
  if (event.data.id === 1 && event.data.result?.protocolVersion) {
    window.parent.postMessage({jsonrpc:"2.0",method:"ui/notifications/initialized"},"*");
    window.parent.postMessage({jsonrpc:"2.0",method:"ui/notifications/size-changed",params:{height:document.body.scrollHeight}},"*");
  }
});
window.parent.postMessage({jsonrpc:"2.0",id:1,method:"ui/initialize",params:{appInfo:{name:"My Scoope diagnostic card",version:"1.0.0"},appCapabilities:{},protocolVersion:"2026-01-26"}},"*");
</script></body></html>"""

    @server.resource("ui://myscoope-dev/meal-card-{version}.html", name="Legacy meal card preview", mime_type=MIME_TYPE)
    def legacy_meal_resource(version: str) -> str:
        if not LEGACY_VERSION_PATTERN.fullmatch(version):
            raise ValueError("Invalid legacy meal card version")
        return card_resource()

    @server.resource("ui://myscoope-dev/entity-card-{version}.html", name="Legacy entity card preview", mime_type=MIME_TYPE)
    def legacy_entity_resource(version: str) -> str:
        if not LEGACY_VERSION_PATTERN.fullmatch(version):
            raise ValueError("Invalid legacy entity card version")
        return entity_resource()

    @server.resource("ui://myscoope-dev/probe-card-{version}.html", name="Legacy diagnostic card preview", mime_type=MIME_TYPE)
    def legacy_probe_resource(version: str) -> str:
        if not LEGACY_VERSION_PATTERN.fullmatch(version):
            raise ValueError("Invalid legacy diagnostic card version")
        return probe_resource()

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
