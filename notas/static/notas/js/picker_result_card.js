function setText(root, role, value, decimals = null) {
  const node = root.querySelector(`[data-role="${role}"]`);
  if (!node) return;

  const numericValue = Number(value) || 0;
  node.textContent = decimals === null
    ? String(value ?? "")
    : numericValue.toFixed(decimals);
}

function setAllocation(root, nutrient, value) {
  const allocation = Number(value) || 0;
  const cell = root.querySelector(`[data-role="result-alloc-${nutrient}"]`);
  const text = root.querySelector(`[data-role="result-alloc-${nutrient}-text"]`);

  cell?.style.setProperty("--alloc", allocation.toFixed(0));
  if (text) text.textContent = `${allocation.toFixed(0)}%`;
}

function renderItems(root, items, emptyLabel) {
  const list = root.querySelector('[data-role="result-items"]');
  if (!list) return;

  list.replaceChildren();

  if (!items.length) {
    const empty = document.createElement("li");
    empty.className = "picker-result-card__empty";
    empty.textContent = emptyLabel;
    list.appendChild(empty);
    return;
  }

  items.forEach(item => {
    const row = document.createElement("li");
    row.className = "picker-result-card__item";
    if (item.isProjected) row.classList.add("picker-result-card__item--projected");

    const identity = document.createElement("div");
    identity.className = "picker-result-card__item-identity";

    const name = document.createElement("strong");
    name.textContent = item.name || "—";
    identity.appendChild(name);

    if (item.isProjected) {
      const badge = document.createElement("span");
      badge.className = "picker-result-card__item-badge";
      badge.textContent = item.projectedLabel || "Por agregar";
      identity.appendChild(badge);
    }

    const meta = document.createElement("span");
    meta.className = "picker-result-card__item-meta";
    meta.textContent = item.meta || "";

    row.append(identity, meta);
    list.appendChild(row);
  });
}

export function projectMealResultItems(existingItems, selectedFood, quantity, editingMealFoodId = null) {
  const currentItems = (existingItems || [])
    .filter(item => Number(item.mealfood_id) !== Number(editingMealFoodId))
    .map(item => ({
      name: item.name,
      meta: `${Number(item.quantity || 0).toFixed(0)} g|ml`,
    }));

  return [
    ...currentItems,
    {
      name: selectedFood.display_name || selectedFood.name,
      meta: `${Number(quantity || 0).toFixed(0)} g|ml`,
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
      name: item.name,
      meta: [item.hour, item.note].filter(Boolean).join(" · "),
    }));

  return [
    ...currentItems,
    {
      name: selectedMeal.name,
      meta: [hour, note].filter(Boolean).join(" · "),
      isProjected: true,
      projectedLabel: editingDailyPlanMealId ? "Reemplazo" : "Por agregar",
    },
  ];
}

export function renderResultCard(container, { scope, name, kpis, items, emptyLabel }) {
  const root = container.querySelector(`[data-scope="${scope}"]`);
  if (!root) return;

  setText(root, "result-name", name);
  setText(root, "result-kcal", kpis.total_kcal, 0);
  setText(root, "result-protein", kpis.protein, 0);
  setText(root, "result-carbs", kpis.carbs, 0);
  setText(root, "result-fat", kpis.fat, 0);
  setText(root, "result-ppk", `${(Number(kpis.ppk) || 0).toFixed(1)}g/kg`);

  setAllocation(root, "protein", kpis.alloc?.protein);
  setAllocation(root, "carbs", kpis.alloc?.carbs);
  setAllocation(root, "fat", kpis.alloc?.fat);
  renderItems(root, items, emptyLabel);
}
