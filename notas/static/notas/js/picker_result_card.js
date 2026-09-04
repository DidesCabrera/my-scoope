const NUTRIENT_ENERGY = {
  protein: 4,
  carbs: 4,
  fat: 9,
};

function numeric(value) {
  return Number(value) || 0;
}

function safePercentage(part, total) {
  const normalizedTotal = numeric(total);
  return normalizedTotal > 0 ? (numeric(part) / normalizedTotal) * 100 : 0;
}

function setText(root, role, value, decimals = null) {
  const node = root.querySelector(`[data-role="${role}"]`);
  if (!node) return;

  node.textContent = decimals === null
    ? String(value ?? "")
    : numeric(value).toFixed(decimals);
}

function setAllocation(root, nutrient, value) {
  const allocation = numeric(value);
  const cell = root.querySelector(`[data-role="result-alloc-${nutrient}"]`);
  const text = root.querySelector(`[data-role="result-alloc-${nutrient}-text"]`);

  cell?.style.setProperty("--alloc", allocation.toFixed(0));
  if (text) text.textContent = `${allocation.toFixed(0)}%`;
}

function createElement(tagName, className = "", text = null) {
  const node = document.createElement(tagName);
  if (className) node.className = className;
  if (text !== null) node.textContent = text;
  return node;
}

function createProjectedBadge(label) {
  return createElement(
    "span",
    "picker-result-badge picker-result-badge--pending",
    label || "Por agregar",
  );
}

function markProjectedRow(row, item) {
  row.dataset.pickerResultRow = "";
  if (!item.isProjected) return;

  row.classList.add("picker-result-row--projected");
  row.dataset.projected = "true";
}

function createNameCell(item, className = "data-grid-cell data-grid-cell--name") {
  const cell = createElement("div", className);
  const line = createElement("span", "picker-result-row__name-line");
  line.appendChild(createElement("span", "picker-result-row__name", item.name || "—"));

  if (item.isProjected) {
    line.appendChild(createProjectedBadge(item.projectedLabel));
  }

  cell.appendChild(line);
  return cell;
}

function createMealIdentity(item) {
  const identity = createElement("span", "data-grid-meal-identity");
  const icon = createElement("i", "data-grid-meal-icon meal");
  icon.dataset.lucide = "utensils";
  icon.setAttribute("aria-hidden", "true");

  const copy = createElement("span", "data-grid-meal-identity__copy");
  const nameLine = createElement("span", "picker-result-row__name-line");
  nameLine.appendChild(createElement("span", "data-grid-meal-name", item.name || "—"));

  if (item.isProjected) {
    nameLine.appendChild(createProjectedBadge(item.projectedLabel));
  }

  copy.appendChild(nameLine);
  if (item.hour) {
    copy.appendChild(createElement("span", "data-grid-meal-time", item.hour));
  }

  identity.append(icon, copy);
  return identity;
}

function createAllocationCell(kind, value) {
  const allocation = numeric(value);
  const cell = createElement("div", "alloc-cell alloc-cell--grid");
  cell.style.setProperty("--alloc", allocation);
  cell.appendChild(createElement("div", `alloc-bar alloc-bar--${kind}`));

  const textClass = allocation > 0 ? "alloc-text alloc-text--shadowed" : "alloc-text";
  cell.appendChild(createElement("span", textClass, `${allocation.toFixed(0)}%`));
  return cell;
}

function createMacroDistribution(distribution) {
  const protein = numeric(distribution?.protein);
  const carbs = numeric(distribution?.carbs);
  const fat = numeric(distribution?.fat);
  const node = createElement("div", "macro-kcal-distribution");
  const description = `Distribución calórica: proteínas ${protein.toFixed(0)}%, carbohidratos ${carbs.toFixed(0)}%, grasas ${fat.toFixed(0)}%`;

  node.setAttribute("role", "img");
  node.setAttribute("aria-label", description);
  node.title = `P ${protein.toFixed(0)}% · C ${carbs.toFixed(0)}% · G ${fat.toFixed(0)}%`;

  Object.entries({ protein, carbs, fat }).forEach(([kind, value]) => {
    if (value <= 0) return;
    const segment = createElement(
      "div",
      `macro-kcal-distribution__segment macro-kcal-distribution__segment--${kind}`,
    );
    segment.style.setProperty("--macro-kcal-share", value);
    node.appendChild(segment);
  });

  return node;
}

function createCell(className, content) {
  const cell = createElement("div", `data-grid-cell ${className}`);
  if (content instanceof Node) {
    cell.appendChild(content);
  } else {
    cell.textContent = String(content ?? "");
  }
  return cell;
}

function renderGrid(root, role, items, buildRow, emptyLabel) {
  const grid = root.querySelector(`[data-role="${role}"]`);
  if (!grid) return;

  grid.querySelectorAll("[data-picker-result-row], .data-grid-empty").forEach(node => node.remove());

  if (!items.length) {
    grid.appendChild(createElement("div", "data-grid-empty", emptyLabel));
    return;
  }

  items.forEach(item => grid.appendChild(buildRow(item)));
}

function createFoodDesktopRow(item) {
  const row = createElement("div", "data-grid-row data-grid-row--foods");
  markProjectedRow(row, item);
  row.append(
    createNameCell(item),
    createCell("data-grid-cell--qty", `${numeric(item.quantity).toFixed(0)} g`),
    createCell("data-grid-cell--kcal data-grid-group-start", numeric(item.total_kcal).toFixed(0)),
    createCell("data-grid-cell--kcal-share", createAllocationCell("kcal", item.kcalShare)),
    createCell("data-grid-cell--macro data-grid-group-start", numeric(item.protein).toFixed(1)),
    createCell("data-grid-cell--macro", numeric(item.carbs).toFixed(1)),
    createCell("data-grid-cell--macro", numeric(item.fat).toFixed(1)),
    createCell("data-grid-cell--kcal-distribution", createMacroDistribution(item.kcalDistribution)),
  );

  const allocation = createElement("div", "data-grid-alloc-group data-grid-group-start");
  allocation.append(
    createCell("data-grid-cell--alloc", createAllocationCell("protein", item.alloc.protein)),
    createCell("data-grid-cell--alloc", createAllocationCell("carbs", item.alloc.carbs)),
    createCell("data-grid-cell--alloc", createAllocationCell("fat", item.alloc.fat)),
  );
  row.appendChild(allocation);
  return row;
}

function createFoodQuantityRow(item) {
  const row = createElement("div", "data-grid-row data-grid-row--mobile-foods-qty");
  markProjectedRow(row, item);
  row.append(
    createNameCell(item),
    createCell("data-grid-cell--qty", `${numeric(item.quantity).toFixed(0)} g`),
  );
  return row;
}

function createFoodCaloriesRow(item) {
  const row = createElement("div", "data-grid-row data-grid-row--mobile-foods-calories");
  markProjectedRow(row, item);
  row.append(
    createNameCell(item),
    createCell("data-grid-cell--kcal", numeric(item.total_kcal).toFixed(0)),
    createCell("data-grid-cell--kcal-share", createAllocationCell("kcal", item.kcalShare)),
  );
  return row;
}

function createFoodMacrosRow(item) {
  const row = createElement("div", "data-grid-row data-grid-row--mobile-foods-macros");
  markProjectedRow(row, item);
  row.append(
    createNameCell(item),
    createCell("data-grid-cell--macro", numeric(item.protein).toFixed(1)),
    createCell("data-grid-cell--macro", numeric(item.carbs).toFixed(1)),
    createCell("data-grid-cell--macro", numeric(item.fat).toFixed(1)),
    createCell("data-grid-cell--kcal-distribution", createMacroDistribution(item.kcalDistribution)),
  );
  return row;
}

function createFoodAllocRow(item) {
  const row = createElement("div", "data-grid-row data-grid-row--mobile-foods-alloc");
  markProjectedRow(row, item);
  row.append(
    createNameCell(item),
    createCell("data-grid-cell--alloc", createAllocationCell("protein", item.alloc.protein)),
    createCell("data-grid-cell--alloc", createAllocationCell("carbs", item.alloc.carbs)),
    createCell("data-grid-cell--alloc", createAllocationCell("fat", item.alloc.fat)),
  );
  return row;
}

function aggregateFoodItems(items) {
  const grouped = new Map();

  items.forEach(item => {
    const key = item.foodId == null ? `name:${item.name}` : `id:${item.foodId}`;
    const current = grouped.get(key) || {
      name: item.name,
      quantity: 0,
      isProjected: false,
      projectedLabel: item.projectedLabel,
    };
    current.quantity += numeric(item.quantity);
    current.isProjected ||= Boolean(item.isProjected);
    grouped.set(key, current);
  });

  return Array.from(grouped.values()).sort((left, right) => (
    right.quantity - left.quantity || left.name.localeCompare(right.name)
  ));
}

function createFoodSummaryRow(item) {
  const row = createElement("div", "data-grid-row data-grid-row--foods-aggregation");
  markProjectedRow(row, item);
  const cell = createElement("div", "data-grid-cell data-grid-cell--foods");
  const line = createElement("span", "picker-result-row__name-line");
  line.appendChild(createElement("span", "picker-result-row__name", `${item.name} (${numeric(item.quantity).toFixed(0)} g)`));
  if (item.isProjected) line.appendChild(createProjectedBadge(item.projectedLabel));
  cell.appendChild(line);
  row.appendChild(cell);
  return row;
}

function createMealDesktopRow(item) {
  const row = createElement("div", "data-grid-row data-grid-row--meals");
  markProjectedRow(row, item);
  const identityCell = createElement("div", "data-grid-cell data-grid-cell--name data-grid-cell--meal-identity");
  identityCell.appendChild(createMealIdentity(item));
  row.append(
    identityCell,
    createCell("data-grid-cell--kcal", numeric(item.total_kcal).toFixed(0)),
    createCell("data-grid-cell--kcal-share", createAllocationCell("kcal", item.kcalShare)),
    createCell("data-grid-cell--macro data-grid-group-start", numeric(item.protein).toFixed(1)),
    createCell("data-grid-cell--macro", numeric(item.carbs).toFixed(1)),
    createCell("data-grid-cell--macro", numeric(item.fat).toFixed(1)),
    createCell("data-grid-cell--kcal-distribution", createMacroDistribution(item.kcalDistribution)),
  );

  const allocation = createElement("div", "data-grid-alloc-group data-grid-group-start");
  allocation.append(
    createCell("data-grid-cell--alloc", createAllocationCell("protein", item.alloc.protein)),
    createCell("data-grid-cell--alloc", createAllocationCell("carbs", item.alloc.carbs)),
    createCell("data-grid-cell--alloc", createAllocationCell("fat", item.alloc.fat)),
  );
  row.appendChild(allocation);
  return row;
}

function createMealMenuRow(item) {
  const row = createElement("div", "data-grid-row data-grid-row--menu");
  markProjectedRow(row, item);
  const mealCell = createElement("div", "data-grid-cell data-grid-cell--meal");
  const title = createElement("span", "data-grid-meal-title");
  title.appendChild(createMealIdentity(item));
  mealCell.appendChild(title);

  const foods = (item.foods || []).map(food => food.name || food.display_name).filter(Boolean);
  row.append(mealCell, createCell("data-grid-cell--foods", foods.join(", ") || "Sin alimentos"));
  return row;
}

function createMealCaloriesRow(item) {
  const row = createElement("div", "data-grid-row data-grid-row--mobile-meals-calories");
  markProjectedRow(row, item);
  row.append(
    createNameCell(item),
    createCell("data-grid-cell--kcal", numeric(item.total_kcal).toFixed(0)),
    createCell("data-grid-cell--kcal-share", createAllocationCell("kcal", item.kcalShare)),
  );
  return row;
}

function createMealMacrosRow(item) {
  const row = createElement("div", "data-grid-row data-grid-row--mobile-macros");
  markProjectedRow(row, item);
  const identityCell = createElement("div", "data-grid-cell data-grid-cell--name data-grid-cell--meal-identity");
  identityCell.appendChild(createMealIdentity(item));
  row.append(
    identityCell,
    createCell("data-grid-cell--macro", numeric(item.protein).toFixed(1)),
    createCell("data-grid-cell--macro", numeric(item.carbs).toFixed(1)),
    createCell("data-grid-cell--macro", numeric(item.fat).toFixed(1)),
    createCell("data-grid-cell--kcal-distribution", createMacroDistribution(item.kcalDistribution)),
  );
  return row;
}

function createMealAllocRow(item) {
  const row = createElement("div", "data-grid-row data-grid-row--mobile-alloc");
  markProjectedRow(row, item);
  const identityCell = createElement("div", "data-grid-cell data-grid-cell--name data-grid-cell--meal-identity");
  identityCell.appendChild(createMealIdentity(item));
  row.append(
    identityCell,
    createCell("data-grid-cell--alloc", createAllocationCell("protein", item.alloc.protein)),
    createCell("data-grid-cell--alloc", createAllocationCell("carbs", item.alloc.carbs)),
    createCell("data-grid-cell--alloc", createAllocationCell("fat", item.alloc.fat)),
  );
  return row;
}

function renderMealPanels(root, items) {
  renderGrid(root, "result-food-summary-grid", aggregateFoodItems(items), createFoodSummaryRow, "No foods yet.");
  renderGrid(root, "result-foods-grid", items, createFoodDesktopRow, "No foods added yet.");
  renderGrid(root, "result-foods-qty-grid", items, createFoodQuantityRow, "No foods added yet.");
  renderGrid(root, "result-foods-calories-grid", items, createFoodCaloriesRow, "No foods added yet.");
  renderGrid(root, "result-foods-macros-grid", items, createFoodMacrosRow, "No foods added yet.");
  renderGrid(root, "result-foods-alloc-grid", items, createFoodAllocRow, "No foods added yet.");
}

function renderDailyPlanPanels(root, items) {
  renderGrid(root, "result-meals-menu-grid", items, createMealMenuRow, "No meals yet.");
  renderGrid(root, "result-meals-grid", items, createMealDesktopRow, "No meals added yet.");
  renderGrid(root, "result-meals-calories-grid", items, createMealCaloriesRow, "No meals added yet.");
  renderGrid(root, "result-meals-macros-grid", items, createMealMacrosRow, "No meals added yet.");
  renderGrid(root, "result-meals-alloc-grid", items, createMealAllocRow, "No meals added yet.");
}

function countUniqueFoods(items, entityKind) {
  const keys = new Set();
  const foods = entityKind === "meal" ? items : items.flatMap(item => item.foods || []);

  foods.forEach(food => {
    const foodId = food.foodId ?? food.id;
    keys.add(foodId == null ? `name:${food.name || food.display_name}` : `id:${foodId}`);
  });

  return keys.size;
}

export function withResultMetrics(items, resultKpis) {
  const totalMacroEnergy = {
    protein: numeric(resultKpis.protein) * NUTRIENT_ENERGY.protein,
    carbs: numeric(resultKpis.carbs) * NUTRIENT_ENERGY.carbs,
    fat: numeric(resultKpis.fat) * NUTRIENT_ENERGY.fat,
  };

  return (items || []).map(item => {
    const macroEnergy = {
      protein: numeric(item.protein) * NUTRIENT_ENERGY.protein,
      carbs: numeric(item.carbs) * NUTRIENT_ENERGY.carbs,
      fat: numeric(item.fat) * NUTRIENT_ENERGY.fat,
    };
    const itemMacroEnergy = macroEnergy.protein + macroEnergy.carbs + macroEnergy.fat;

    return {
      ...item,
      kcalShare: safePercentage(item.total_kcal, resultKpis.total_kcal),
      kcalDistribution: {
        protein: safePercentage(macroEnergy.protein, itemMacroEnergy),
        carbs: safePercentage(macroEnergy.carbs, itemMacroEnergy),
        fat: safePercentage(macroEnergy.fat, itemMacroEnergy),
      },
      alloc: {
        protein: safePercentage(macroEnergy.protein, totalMacroEnergy.protein),
        carbs: safePercentage(macroEnergy.carbs, totalMacroEnergy.carbs),
        fat: safePercentage(macroEnergy.fat, totalMacroEnergy.fat),
      },
    };
  });
}

export function projectMealResultItems(existingItems, selectedFood, quantity, editingMealFoodId = null) {
  const currentItems = (existingItems || [])
    .filter(item => Number(item.mealfood_id) !== Number(editingMealFoodId))
    .map(item => ({
      foodId: item.food_id,
      name: item.name,
      quantity: numeric(item.quantity),
      protein: numeric(item.protein),
      carbs: numeric(item.carbs),
      fat: numeric(item.fat),
      total_kcal: numeric(item.total_kcal),
    }));
  const factor = numeric(quantity) / 100;

  return [
    ...currentItems,
    {
      foodId: selectedFood.id,
      name: selectedFood.display_name || selectedFood.name,
      quantity: numeric(quantity),
      protein: numeric(selectedFood.protein) * factor,
      carbs: numeric(selectedFood.carbs) * factor,
      fat: numeric(selectedFood.fat) * factor,
      total_kcal: numeric(selectedFood.total_kcal) * factor,
      isProjected: true,
      projectedLabel: editingMealFoodId ? "Reemplazo" : "Por agregar",
    },
  ];
}

export function projectDailyPlanResultItems(
  existingItems,
  selectedMeal,
  { hour = "", note = "", editingDailyPlanMealId = null } = {},
) {
  const currentItems = (existingItems || [])
    .filter(item => Number(item.dailyplanmeal_id) !== Number(editingDailyPlanMealId))
    .map(item => ({
      mealId: item.meal_id,
      name: item.name,
      hour: item.hour,
      note: item.note,
      protein: numeric(item.protein),
      carbs: numeric(item.carbs),
      fat: numeric(item.fat),
      total_kcal: numeric(item.total_kcal),
      foods: item.foods || [],
    }));

  return [
    ...currentItems,
    {
      mealId: selectedMeal.id,
      name: selectedMeal.name,
      hour,
      note,
      protein: numeric(selectedMeal.protein),
      carbs: numeric(selectedMeal.carbs),
      fat: numeric(selectedMeal.fat),
      total_kcal: numeric(selectedMeal.total_kcal),
      foods: selectedMeal.foods || [],
      isProjected: true,
      projectedLabel: editingDailyPlanMealId ? "Reemplazo" : "Por agregar",
    },
  ];
}

export function renderResultCard(container, {
  scope,
  name,
  owner,
  kpis,
  items,
  entityKind,
}) {
  const root = container.querySelector(`[data-scope="${scope}"]`);
  if (!root) return;

  const resultItems = withResultMetrics(items, kpis);

  setText(root, "result-name", name);
  setText(root, "result-owner", owner);
  setText(root, "result-kcal", kpis.total_kcal, 0);
  setText(root, "result-protein", kpis.protein, 0);
  setText(root, "result-carbs", kpis.carbs, 0);
  setText(root, "result-fat", kpis.fat, 0);
  setText(root, "result-ppk", `${numeric(kpis.ppk).toFixed(1)}g/kg`);
  setText(root, "result-food-count", countUniqueFoods(resultItems, entityKind));
  if (entityKind === "dailyplan") setText(root, "result-meal-count", resultItems.length);

  setAllocation(root, "protein", kpis.alloc?.protein);
  setAllocation(root, "carbs", kpis.alloc?.carbs);
  setAllocation(root, "fat", kpis.alloc?.fat);

  if (entityKind === "meal") {
    renderMealPanels(root, resultItems);
  } else {
    renderDailyPlanPanels(root, resultItems);
  }

  window.lucide?.createIcons?.();
}
