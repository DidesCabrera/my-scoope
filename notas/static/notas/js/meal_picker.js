// ======================================================
// meal_picker.js
// ADD / EDIT explícito vía MEAL_PICKER_CONTEXT
// ======================================================

import {
  addKpis,
  subtractKpis,
  computeAlloc,
  computePPK
} from "./meal_math.js";

import {
  renderSelectedMeal,
  renderDayPreview,
  renderFoodsAggregation
} from "./meal_preview.js";

import { renderMealItem } from "./meal_item_list.js";

document.addEventListener("DOMContentLoaded", () => {
  const ctx = window.MEAL_PICKER_CONTEXT;
  const pickerData = window.MEAL_PICKER_DATA || {};

  const browseMeals = pickerData.browse_meals || [];
  const existingMeals = pickerData.existing_meals || [];

  const mealById = new Map();

  browseMeals.forEach(meal => {
    if (meal && meal.id != null) {
      mealById.set(Number(meal.id), meal);
    }
  });

  existingMeals.forEach(meal => {
    if (meal && meal.id != null) {
      mealById.set(Number(meal.id), meal);
    }
  });

  const picker = document.getElementById("meal-picker");
  const previewRoot = document.getElementById("dp-preview");

  if (!picker || !ctx) return;

  // ---------------------------
  // DOM
  // ---------------------------

  const input = document.getElementById("meal-search");
  const list = document.getElementById("meal-list");
  const hidden = document.getElementById("dp-selected-meal-id");
  const previewBox = document.getElementById("dp-preview");
  const form = document.getElementById("dp-form");

  if (!input || !list || !hidden || !previewBox || !form) return;

  const hourInput = form.querySelector('input[name="hour"]');
  const noteInput = form.querySelector('input[name="note"]');
  const title = document.getElementById("meal-form-title");

  const btnAdd = document.getElementById("btn-add-meal");
  const btnUpdate = document.getElementById("btn-update-meal");
  const btnCancel = document.getElementById("btn-cancel-meal-edit");
  const btnCancelInline = document.getElementById("btn-cancel-picker-inline-meal");

  const ADD_ACTION = form.action;

  let selectedMeal = null;

  // ---------------------------
  // Helpers
  // ---------------------------

  function isEdit() {
    return ctx.mode === "edit";
  }

  function openList() {
    list.style.display = "block";
  }

  function closeList() {
    list.style.display = "none";
  }

  function isMobileViewport() {
    return window.innerWidth <= 768;
  }

  function getPickerSection() {
    return (
      picker.closest(".section-picker") ||
      picker.closest("[id$='picker-section']") ||
      picker.closest(".add-row") ||
      picker
    );
  }

  function getPickerScrollTarget() {
    const pickerSection = getPickerSection();

    return (
      pickerSection.querySelector(".title-section-panels") ||
      title?.closest(".title-section-panels") ||
      pickerSection
    );
  }

  function scrollPickerIntoMobileView() {
    if (!isMobileViewport()) return;
  
    const targetElement = getPickerScrollTarget();
    if (!targetElement) return;
  
    const topOffset = 0;
    const rect = targetElement.getBoundingClientRect();
    const targetY = window.scrollY + rect.top - topOffset;
  
    window.scrollTo({
      top: Math.max(targetY, 0),
      behavior: "smooth",
    });
  }

  function schedulePickerScrollIntoMobileView() {
    if (!isMobileViewport()) return;

    window.setTimeout(scrollPickerIntoMobileView, 80);
    window.setTimeout(scrollPickerIntoMobileView, 260);
  }

  function clearSelection() {
    selectedMeal = null;
    hidden.value = "";
    input.value = "";

    previewBox.style.display = "none";
    form.classList.remove("has-selection");

    if (btnCancelInline) {
      btnCancelInline.style.display = "inline-block";
    }
  }

  function applySelectedMeal(meal) {
    if (!meal) return;

    selectedMeal = meal;
    hidden.value = meal.id;
    input.value = meal.name;

    showPreview();
    form.classList.add("has-selection");
  }

  function enterAddMode() {
    ctx.mode = "add";
    ctx.editing = null;
    form.action = ADD_ACTION;

    if (btnAdd) btnAdd.style.display = "inline-block";
    if (btnUpdate) btnUpdate.style.display = "none";
    if (btnCancel) btnCancel.style.display = "inline-block";

    if (hourInput) hourInput.value = "";
    if (noteInput) noteInput.value = "";

    if (title) title.textContent = "Agrega una Comida";
  }

  function enterEditMode() {
    if (btnAdd) btnAdd.style.display = "none";
    if (btnUpdate) btnUpdate.style.display = "inline-block";
    if (btnCancel) btnCancel.style.display = "inline-block";

    if (title) title.textContent = "Reemplaza la Comida";
  }

  function findMealById(mealId) {
    if (mealId == null || mealId === "") return null;
    return mealById.get(Number(mealId)) || null;
  }

  function expandPickerSection() {
    const pickerSection = document.getElementById("dailyplan-picker-section");
    const pickerToggle = document.querySelector(
      '.js-picker-toggle[aria-controls="dailyplan-picker-section"]'
    );

    if (pickerSection) {
      pickerSection.classList.remove("is-collapsed");
    }

    if (pickerToggle) {
      pickerToggle.setAttribute("aria-expanded", "true");
    }
  }

  // ---------------------------
  // Meal list
  // ---------------------------

  function renderMealList(items) {
    list.innerHTML = "";
  
    if (!Array.isArray(items) || !items.length) {
      list.innerHTML = `<li class="empty">No meals found</li>`;
      return;
    }
  
    items.forEach(meal => {
      if (!meal || !meal.name) return;
  
      try {
        const li = document.createElement("li");
        li.className = "picker-list-item meal-item";
        li.innerHTML = renderMealItem(meal);
  
        li.addEventListener("click", () => {
          applySelectedMeal(meal);
  
          if (btnCancelInline) {
            btnCancelInline.style.display = "none";
          }
  
          closeList();
        });
  
        list.appendChild(li);
      } catch (error) {
        console.error("Error rendering meal item", error, meal);
      }
    });
  
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  }

  // ---------------------------
  // Preview
  // ---------------------------

  function showPreview() {
    if (!selectedMeal) return;

    let basePlanKpis = ctx.dailyplan.kpis;

    if (isEdit() && ctx.editing?.original_kpis) {
      basePlanKpis = subtractKpis(
        ctx.dailyplan.kpis,
        ctx.editing.original_kpis
      );
    }

    const selectedMealKpis = {
      protein: selectedMeal.protein,
      carbs: selectedMeal.carbs,
      fat: selectedMeal.fat,
      total_kcal: selectedMeal.total_kcal,
    };

    const previewPlanKpis = addKpis(basePlanKpis, selectedMealKpis);

    const currentWithAlloc = {
      ...basePlanKpis,
      alloc: computeAlloc(basePlanKpis),
    };

    const previewWithAlloc = {
      ...previewPlanKpis,
      alloc: computeAlloc(previewPlanKpis),
    };

    const weight = ctx.dailyplan.kpis.weight;

    currentWithAlloc.ppk = computePPK(currentWithAlloc.protein, weight);
    previewWithAlloc.ppk = computePPK(previewWithAlloc.protein, weight);

    renderSelectedMeal(previewRoot, selectedMeal);
    renderFoodsAggregation(previewRoot, selectedMeal.foods || []);
    renderDayPreview(
      previewRoot,
      currentWithAlloc,
      previewWithAlloc,
      selectedMeal
    );

    previewBox.style.display = "block";
  }

  // ---------------------------
  // Events
  // ---------------------------

  input.addEventListener("focus", () => {
    openList();
    renderMealList(browseMeals);
    schedulePickerScrollIntoMobileView();
  });

  input.addEventListener("input", () => {
    const raw = input.value || "";
    const q = raw.trim().toLowerCase();

    if (!q) {
      clearSelection();
      enterAddMode();
      renderMealList(browseMeals);
      openList();
      return;
    }

    const filteredMeals = browseMeals.filter(meal =>
      meal.name.toLowerCase().includes(q)
    );

    renderMealList(filteredMeals);
    openList();
  });

  document.addEventListener("mousedown", e => {
    if (!picker.contains(e.target)) {
      closeList();
    }
  });

  // ---------------------------
  // EDIT / REPLACE
  // ---------------------------

  document.querySelectorAll(".edit-meal-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      ctx.mode = "edit";
      ctx.editing = {
        dailyplanmeal_id: Number(btn.dataset.dpmId),
        hour: btn.dataset.hour || "",
        note: btn.dataset.note || "",
        original_kpis: {
          protein: Number(btn.dataset.protein),
          carbs: Number(btn.dataset.carbs),
          fat: Number(btn.dataset.fat),
          total_kcal: Number(btn.dataset.kcal),
        }
      };

      if (hourInput) hourInput.value = ctx.editing.hour;
      if (noteInput) noteInput.value = ctx.editing.note;

      const mealId = Number(btn.dataset.mealId);
      const meal = findMealById(mealId);

      if (!meal) {
        console.warn("Meal no encontrada para edit:", mealId);
        return;
      }

      form.action = `/app/dailyplans/${ctx.dailyplan.id}/meals/${ctx.editing.dailyplanmeal_id}/update/`;

      document.dispatchEvent(new CustomEvent("picker:open", {
        detail: { sectionId: "dailyplan-picker-section" }
      }));

      enterEditMode();
      applySelectedMeal(meal);
      schedulePickerScrollIntoMobileView();

      if (btnCancelInline) {
        btnCancelInline.style.display = "none";
      }

      closeList();
    });
  });

  // ---------------------------
  // CANCEL EDIT
  // ---------------------------

  if (btnCancel) {
    btnCancel.addEventListener("click", () => {
      clearSelection();
      enterAddMode();
      closeList();

      document.dispatchEvent(new CustomEvent("picker:close", {
        detail: { sectionId: "dailyplan-picker-section" }
      }));
    });
  }

  if (btnCancelInline) {
    btnCancelInline.addEventListener("click", () => {
      clearSelection();
      enterAddMode();
      closeList();

      document.dispatchEvent(new CustomEvent("picker:close", {
        detail: { sectionId: "dailyplan-picker-section" }
      }));
    });
  }

  // ---------------------------
  // INITIAL MEAL FROM URL
  // ---------------------------

  const initialMealId = window.dailyplanInitialMeal;

  if (initialMealId) {
    const meal = findMealById(initialMealId);

    if (meal) {
      expandPickerSection();
      applySelectedMeal(meal);

      if (btnCancelInline) {
        btnCancelInline.style.display = "none";
      }

      closeList();

      const url = new URL(window.location);
      url.searchParams.delete("select_meal");
      window.history.replaceState({}, "", url);
    }
  }
});