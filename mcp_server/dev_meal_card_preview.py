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


def current_css() -> str:
    match = STYLE_PATTERN.search(SOURCE_PATH.read_text(encoding="utf-8"))
    if not match:
        raise ValueError("Meal card source has no style block")
    return match.group(1)


def preview_html() -> str:
    html = CARD_PATH.read_text(encoding="utf-8")
    live_script = """
<script>
(() => {
  let requestId = 1000;
  let lastCss = null;
  function refreshStyles() {
    window.parent.postMessage({
      jsonrpc: "2.0", id: ++requestId, method: "tools/call",
      params: {name: "preview_card_styles", arguments: {}}
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
        raise ValueError("Meal card HTML has no body closing tag")
    return html.replace("</body>", live_script + "</body>", 1)


def create_preview_server() -> FastMCP:
    # A new URI per process avoids a stale cached resource when HTML changes.
    uri = f"ui://myscoope-dev/meal-card-{uuid.uuid4().hex}.html"
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
        name="preview_card_styles",
        description="Read local meal card CSS for the preview iframe.",
        meta={"ui": {"visibility": ["app"]}},
        structured_output=True,
    )
    def preview_card_styles() -> dict[str, str]:
        return {"css": current_css()}

    @server.resource(uri, name="My Scoope meal card development preview", mime_type=MIME_TYPE)
    def card_resource() -> str:
        return preview_html()

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
