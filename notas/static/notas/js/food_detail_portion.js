// ======================================================
// food_detail_portion.js
// Recalcula los KPI del detalle de Food según porción.
// ======================================================

import { computeAlloc, computePPK, portionFromFood } from "./food_math.js";

function toNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function formatNumber(value, decimals = 0) {
  return toNumber(value).toFixed(decimals);
}

function setText(root, selector, value) {
  const element = root.querySelector(selector);
  if (!element) return;
  element.textContent = value;
}

function setAlloc(row, value) {
  if (!row) return;

  const safeValue = Math.max(0, toNumber(value));
  const pctText = row.querySelector(".alloc-pct p");
  const bar = row.querySelector(".alloc-bar-comp");

  if (pctText) {
    pctText.textContent = `${formatNumber(safeValue, 0)}%`;
  }

  if (bar) {
    bar.style.setProperty("--alloc", formatNumber(safeValue, 3));
  }
}

function getRows(root) {
  const rows = root.querySelectorAll(".kpi-row");

  return {
    protein: rows[0] || null,
    carbs: rows[1] || null,
    fat: rows[2] || null,
  };
}

function renderFoodDetailPortion(root, grams) {
  const baseFood = {
    protein: toNumber(root.dataset.baseProtein),
    carbs: toNumber(root.dataset.baseCarbs),
    fat: toNumber(root.dataset.baseFat),
    total_kcal: toNumber(root.dataset.baseKcal),
  };

  const currentWeight = toNumber(root.dataset.currentWeight);
  const portion = portionFromFood(baseFood, grams);
  const alloc = computeAlloc(portion);
  const rows = getRows(root);

  setText(root, ".tot h2", formatNumber(portion.total_kcal, 0));
  setText(rows.protein, ".kpi-grams", `${formatNumber(portion.protein, 0)}g`);
  setText(rows.carbs, ".kpi-grams", `${formatNumber(portion.carbs, 0)}g`);
  setText(rows.fat, ".kpi-grams", `${formatNumber(portion.fat, 0)}g`);

  const ppk = computePPK(portion.protein, currentWeight);
  setText(rows.protein, ".proteins_per_kilo", `${formatNumber(ppk, 1)}g/kg`);

  setAlloc(rows.protein, alloc.protein);
  setAlloc(rows.carbs, alloc.carbs);
  setAlloc(rows.fat, alloc.fat);
}

document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-food-detail-portion]");
  if (!root) return;

  const input = document.getElementById("food-detail-quantity");
  if (!input) return;

  function sync() {
    const grams = Math.max(0, toNumber(input.value));
    renderFoodDetailPortion(root, grams);
  }

  input.addEventListener("input", sync);
  input.addEventListener("change", sync);
  sync();
});
