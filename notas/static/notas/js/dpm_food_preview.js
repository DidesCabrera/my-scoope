// ======================================================
// dpm_food_preview.js
// Render DOM: Food / Meal / DailyPlan
// ======================================================

import { computeAlloc } from "./dpm_food_math.js";

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

// -------- FOOD BASE (100g)
export function renderBase(food) {
  const basisUnit = document.querySelector('[data-scope="food-preview"] [data-role="food-basis-unit"]');
  if (basisUnit) basisUnit.textContent = `100${food.quantity_unit || "g"}`;
  const alloc = computeAlloc(food);

  setValue("base-kcal", food.total_kcal, 0);
  setValue("base-protein", food.protein, 0);
  setValue("base-carbs", food.carbs, 0);
  setValue("base-fat", food.fat, 0);

  setAlloc("base-alloc-protein-cell", "base-alloc-protein-text", alloc.protein);
  setAlloc("base-alloc-carbs-cell", "base-alloc-carbs-text", alloc.carbs);
  setAlloc("base-alloc-fat-cell", "base-alloc-fat-text", alloc.fat);
}

// -------- FOOD PORTION
export function renderPortion(portion) {
  const alloc = computeAlloc(portion);

  // Impacto / tabla preview
  setValue("qty-kcal", portion.total_kcal, 0);
  setValue("qty-protein", portion.protein, 0);
  setValue("qty-carbs", portion.carbs, 0);
  setValue("qty-fat", portion.fat, 0);

  setAlloc("qty-alloc-protein-cell", "qty-alloc-protein-text", alloc.protein);
  setAlloc("qty-alloc-carbs-cell", "qty-alloc-carbs-text", alloc.carbs);
  setAlloc("qty-alloc-fat-cell", "qty-alloc-fat-text", alloc.fat);

  // KPI superior del picker
  setValue("base-kcal", portion.total_kcal, 0);
  setValue("base-protein", portion.protein, 0);
  setValue("base-carbs", portion.carbs, 0);
  setValue("base-fat", portion.fat, 0);

  setAlloc("base-alloc-protein-cell", "base-alloc-protein-text", alloc.protein);
  setAlloc("base-alloc-carbs-cell", "base-alloc-carbs-text", alloc.carbs);
  setAlloc("base-alloc-fat-cell", "base-alloc-fat-text", alloc.fat);
}

// -------- MEAL PREVIEW
export function renderPreviewTotals(previewTotals) {
  const alloc = computeAlloc(previewTotals);

  setValue("meal-prev-kcal", previewTotals.total_kcal, 0);
  setValue("meal-prev-protein", previewTotals.protein, 0);
  setValue("meal-prev-carbs", previewTotals.carbs, 0);
  setValue("meal-prev-fat", previewTotals.fat, 0);

  setAlloc("meal-prev-alloc-protein-cell", "meal-prev-alloc-protein-text", alloc.protein);
  setAlloc("meal-prev-alloc-carbs-cell", "meal-prev-alloc-carbs-text", alloc.carbs);
  setAlloc("meal-prev-alloc-fat-cell", "meal-prev-alloc-fat-text", alloc.fat);

  const mealPpkNode = document.querySelector('[data-role="meal-prev-ppk"]');
  if (mealPpkNode && previewTotals.ppk !== undefined) {
    mealPpkNode.textContent = `${previewTotals.ppk.toFixed(1)}g/kg`;
  }
}

// -------- DAILYPLAN PREVIEW
export function renderDailyPlanPreview(dpTotals, portion = null) {
  const alloc = computeAlloc(dpTotals);

  setValue("dailyplan-prev-kcal", dpTotals.total_kcal, 0);
  setValue("dailyplan-prev-protein", dpTotals.protein, 0);
  setValue("dailyplan-prev-carbs", dpTotals.carbs, 0);
  setValue("dailyplan-prev-fat", dpTotals.fat, 0);

  setAlloc("dailyplan-prev-alloc-protein-cell", "dailyplan-prev-alloc-protein-text", alloc.protein);
  setAlloc("dailyplan-prev-alloc-carbs-cell", "dailyplan-prev-alloc-carbs-text", alloc.carbs);
  setAlloc("dailyplan-prev-alloc-fat-cell", "dailyplan-prev-alloc-fat-text", alloc.fat);

  if (portion) {
    setValue("dailyplan-impact-kcal", portion.total_kcal, 0);
    setValue("dailyplan-impact-protein", portion.protein, 0);
    setValue("dailyplan-impact-carbs", portion.carbs, 0);
    setValue("dailyplan-impact-fat", portion.fat, 0);
  }

  const dailyPlanPpkNode = document.querySelector('[data-role="dailyplan-prev-ppk"]');
  if (dailyPlanPpkNode && dpTotals.ppk !== undefined) {
    dailyPlanPpkNode.textContent = `${dpTotals.ppk.toFixed(1)}g/kg`;
  }
}

// -------- DPM ALLOC (Meal vs DailyPlan)
export function renderDpmAlloc(mealTotals, dailyplanTotals) {
  const alloc = {
    protein: dailyplanTotals.protein
      ? (mealTotals.protein / dailyplanTotals.protein) * 100
      : 0,
    carbs: dailyplanTotals.carbs
      ? (mealTotals.carbs / dailyplanTotals.carbs) * 100
      : 0,
    fat: dailyplanTotals.fat
      ? (mealTotals.fat / dailyplanTotals.fat) * 100
      : 0,
  };

  setAlloc("dpm-alloc-protein-cell", "dpm-alloc-protein-text", alloc.protein);
  setAlloc("dpm-alloc-carbs-cell", "dpm-alloc-carbs-text", alloc.carbs);
  setAlloc("dpm-alloc-fat-cell", "dpm-alloc-fat-text", alloc.fat);
}
