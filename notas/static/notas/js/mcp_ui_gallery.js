(() => {
  const frame = document.getElementById("mcp-meal-frame");
  const stage = document.getElementById("mcp-meal-stage");
  const scenario = document.getElementById("mcp-meal-scenario");
  if (!frame || !stage || !scenario) return;

  const desktopMeal = {
    id: 23,
    name: "Porotos negros con arroz y palta",
    category: "Almuerzo",
    kpis: {
      total_kcal: 931, protein: 40, carbs: 173, fat: 9.1, ppk: 0.5,
      kcal_protein: 160, kcal_carbs: 692, kcal_fat: 81,
      alloc_protein: 17, alloc_carbs: 74, alloc_fat: 9,
    },
    foods: [
      { food_name: "Porotos negros cocidos", quantity: 340, total_kcal: 459, protein: 30.1, carbs: 80.6, fat: 1.8, emoji: "🫘" },
      { food_name: "Arroz blanco cocido", quantity: 300, total_kcal: 378, protein: 8.1, carbs: 84.5, fat: 0.8, emoji: "🍚" },
      { food_name: "Palta", quantity: 42, total_kcal: 73, protein: 0.8, carbs: 3.6, fat: 6.2, emoji: "🥑" },
      { food_name: "Tomate", quantity: 100, total_kcal: 21, protein: 0.9, carbs: 3.9, fat: 0.2, emoji: "🍅" },
    ],
  };
  const mobileMeal = {
    id: 24,
    name: "Avena con yogur, plátano y arándanos",
    category: "Desayuno",
    kpis: {
      total_kcal: 447, protein: 27, carbs: 75, fat: 5, ppk: 0.3,
      kcal_protein: 108, kcal_carbs: 300, kcal_fat: 45,
      alloc_protein: 24, alloc_carbs: 67, alloc_fat: 9,
    },
    foods: [
      { food_name: "Avena tradicional", quantity: 50, total_kcal: 191, protein: 7, carbs: 34, fat: 3, emoji: "🥣" },
      { food_name: "Yogur griego natural sin azúcar", quantity: 180, total_kcal: 107, protein: 19, carbs: 7, fat: 1, emoji: "🥛" },
      { food_name: "Plátano", quantity: 100, total_kcal: 99, protein: 1, carbs: 23, fat: 0, emoji: "🍌" },
      { food_name: "Arándanos", quantity: 80, total_kcal: 51, protein: 1, carbs: 12, fat: 0, emoji: "🫐" },
    ],
  };
  let ready = false;

  function resultForScenario() {
    if (scenario.value === "error") {
      return { ok: false, data: {}, error: { code: "not_found" } };
    }
    const source = scenario.value === "mobile" ? mobileMeal : desktopMeal;
    const sample = { ...source, foods: source.foods };
    if (scenario.value === "long") {
      sample.name = "Almuerzo con vegetales, arroz integral y proteína para un día de entrenamiento";
      sample.foods = [
        { food_name: "Mezcla de vegetales asados con especias y hierbas frescas", quantity: 240, total_kcal: 110, protein: 3, carbs: 19, fat: 2 },
        ...desktopMeal.foods,
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
