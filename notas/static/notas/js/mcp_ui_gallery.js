(() => {
  const frame = document.getElementById("mcp-meal-frame");
  const stage = document.getElementById("mcp-meal-stage");
  const scenario = document.getElementById("mcp-meal-scenario");
  if (!frame || !stage || !scenario) return;

  const meal = {
    id: 23,
    name: "Almuerzo de ejemplo",
    category: "Almuerzo",
    kpis: { total_kcal: 614.4, protein: 35.5, carbs: 74.2, fat: 19.1 },
    foods: [
      { food_name: "Arroz integral", quantity: 180 },
      { food_name: "Pollo a la plancha", quantity: 120 },
    ],
  };
  let ready = false;

  function resultForScenario() {
    if (scenario.value === "error") {
      return { ok: false, data: {}, error: { code: "not_found" } };
    }
    const sample = { ...meal, foods: meal.foods };
    if (scenario.value === "long") {
      sample.name = "Almuerzo con vegetales, arroz integral y proteína para un día de entrenamiento";
      sample.foods = [
        { food_name: "Mezcla de vegetales asados con especias y hierbas frescas", quantity: 240 },
        ...meal.foods,
      ];
    }
    if (scenario.value === "empty") sample.foods = [];
    return { ok: true, data: { meal: sample }, error: null };
  }

  function sendResult() {
    if (!ready || !frame.contentWindow) return;
    frame.contentWindow.postMessage({
      jsonrpc: "2.0",
      method: "ui/notifications/tool-result",
      params: { structuredContent: resultForScenario() },
    }, "*");
  }

  function respondToInitialize(id = 1) {
    frame.contentWindow?.postMessage({
      jsonrpc: "2.0",
      id,
      result: {
        protocolVersion: "2026-01-26",
        hostCapabilities: {},
        hostInfo: { name: "My Scoope UI Gallery", version: "1.0.0" },
        hostContext: { theme: stage.dataset.theme },
      },
    }, "*");
  }

  window.addEventListener("message", (event) => {
    if (event.source !== frame.contentWindow || event.data?.jsonrpc !== "2.0") return;
    const message = event.data;
    if (message.method === "ui/initialize") respondToInitialize(message.id);
    if (message.method === "ui/notifications/initialized") {
      ready = true;
      sendResult();
    }
    if (message.method === "ui/notifications/size-changed") {
      const height = Number(message.params?.height);
      if (Number.isFinite(height) && height > 0) frame.style.height = `${Math.max(340, Math.ceil(height))}px`;
    }
  });
  frame.addEventListener("load", () => respondToInitialize());

  function select(groupSelector, selected, key) {
    document.querySelectorAll(groupSelector).forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset[key] === selected));
    });
  }

  document.querySelectorAll("[data-mcp-theme]").forEach((button) => {
    button.addEventListener("click", () => {
      const theme = button.dataset.mcpTheme;
      stage.dataset.theme = theme;
      frame.style.colorScheme = theme;
      select("[data-mcp-theme]", theme, "mcpTheme");
      frame.contentWindow?.postMessage({
        jsonrpc: "2.0",
        method: "ui/notifications/host-context-changed",
        params: { theme },
      }, "*");
    });
  });
  document.querySelectorAll("[data-mcp-width]").forEach((button) => {
    button.addEventListener("click", () => {
      const width = button.dataset.mcpWidth;
      frame.style.width = `${width}px`;
      select("[data-mcp-width]", width, "mcpWidth");
    });
  });
  scenario.addEventListener("change", sendResult);
})();
