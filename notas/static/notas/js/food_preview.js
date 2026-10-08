// ======================================================
// food_preview.js
// Funciones dedicadas a pintar el preview en el DOM.
// (No hacen cálculos — solo reciben datos listos)
// ======================================================

import { computeAlloc } from "./food_math.js";

function setAlloc(cellId, textId, value) {
  const cell = document.getElementById(cellId);
  const text = document.getElementById(textId);

  if (!cell || !text) return;

  cell.style.setProperty("--alloc", value.toFixed(0));
  text.textContent = value.toFixed(0) + "%";
}

function setValue(id, value, decimals = 0) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value.toFixed(decimals);
}

// -------- BASE (100 g)
export function renderBase(food) {
  const basisUnit = document.querySelector('[data-scope="food-preview"] [data-role="food-basis-unit"]');
  if (basisUnit) basisUnit.textContent = `100${food.quantity_unit || "g"}`;
  const base = {
    protein: food.protein,
    carbs: food.carbs,
    fat: food.fat,
    total_kcal: food.total_kcal,
  };

  const alloc = computeAlloc(base);

  setValue("base-protein", base.protein, 0);
  setValue("base-carbs", base.carbs, 0);
  setValue("base-fat", base.fat, 0);
  setValue("base-kcal", base.total_kcal, 0);

  setAlloc("base-alloc-protein-cell", "base-alloc-protein-text", alloc.protein);
  setAlloc("base-alloc-carbs-cell", "base-alloc-carbs-text", alloc.carbs);
  setAlloc("base-alloc-fat-cell", "base-alloc-fat-text", alloc.fat);
}

// -------- PORCIÓN (cantidad seleccionada)
export function renderPortion(portion) {
  const alloc = computeAlloc(portion);

  // Impacto / tabla preview
  setValue("qty-protein", portion.protein, 0);
  setValue("qty-carbs", portion.carbs, 0);
  setValue("qty-fat", portion.fat, 0);
  setValue("qty-kcal", portion.total_kcal, 0);

  // KPI superior del picker
  setValue("base-protein", portion.protein, 0);
  setValue("base-carbs", portion.carbs, 0);
  setValue("base-fat", portion.fat, 0);
  setValue("base-kcal", portion.total_kcal, 0);

  setAlloc("base-alloc-protein-cell", "base-alloc-protein-text", alloc.protein);
  setAlloc("base-alloc-carbs-cell", "base-alloc-carbs-text", alloc.carbs);
  setAlloc("base-alloc-fat-cell", "base-alloc-fat-text", alloc.fat);
}

// -------- PREVIEW RESULTANTE
export function renderPreviewTotals(previewTotals) {
  const alloc = computeAlloc(previewTotals);

  setValue("meal-prev-kcal", previewTotals.total_kcal, 0);
  setValue("meal-prev-protein", previewTotals.protein, 0);
  setValue("meal-prev-carbs", previewTotals.carbs, 0);
  setValue("meal-prev-fat", previewTotals.fat, 0);

  setAlloc("meal-prev-alloc-protein-cell", "meal-prev-alloc-protein-text", alloc.protein);
  setAlloc("meal-prev-alloc-carbs-cell", "meal-prev-alloc-carbs-text", alloc.carbs);
  setAlloc("meal-prev-alloc-fat-cell", "meal-prev-alloc-fat-text", alloc.fat);

  const ppkNode = document.querySelector('[data-role="prev-ppk"]');
  if (ppkNode && previewTotals.ppk !== undefined) {
    ppkNode.textContent = `${previewTotals.ppk.toFixed(1)}g/kg`;
  }
}
