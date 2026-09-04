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
  renderFoodsAggregation
} from "./meal_preview.js";

import { renderMealItem } from "./meal_item_list.js";
import {
  projectDailyPlanResultItems,
  renderResultCard
} from "./picker_result_card.js";

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
  
    const selector = input.closest(".selector");
    if (selector) {
      selector.classList.add("is-picker-list-open");
    }
  
    ensurePickerCloseButton();
  }
  
  function closeList() {
    list.style.display = "none";
  
    const selector = input.closest(".selector");
    if (selector) {
      selector.classList.remove("is-picker-list-open");
    }
  }

  function clearSelection() {
    selectedMeal = null;
    hidden.value = "";
    input.value = "";

    previewBox.style.display = "none";
    form.classList.remove("has-selection");

  }

  function applySelectedMeal(meal) {
    if (!meal) return;

    selectedMeal = meal;
    hidden.value = meal.id;
    input.value = meal.name;

    showPreview();
    form.classList.add("has-selection");
  }

  function showImpactStep() {
    document.dispatchEvent(new CustomEvent("picker:step", {
      detail: { sectionId: "dailyplan-picker-section", step: "impact" }
    }));
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

  function ensurePickerCloseButton() {
    const selector = input.closest(".selector");
    if (!selector) return null;
  
    let closeButton = selector.querySelector(".picker-list-close-btn");
  
    if (!closeButton) {
      closeButton = document.createElement("button");
      closeButton.type = "button";
      closeButton.className = "picker-list-close-btn";
      closeButton.setAttribute("aria-label", "Cerrar lista");
      closeButton.innerHTML = `<i data-lucide="x"></i>`;
  
      closeButton.addEventListener("click", () => {
        closeList();
        input.blur();
      });
  
      selector.appendChild(closeButton);
    }
  
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  
    return closeButton;
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
  
          closeList();
          showImpactStep();
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

    const previewWithAlloc = {
      ...previewPlanKpis,
      alloc: computeAlloc(previewPlanKpis),
    };

    const weight = ctx.dailyplan.kpis.weight;

    previewWithAlloc.ppk = computePPK(previewWithAlloc.protein, weight);

    renderSelectedMeal(previewRoot, selectedMeal);
    renderFoodsAggregation(previewRoot, selectedMeal.foods || []);
    renderResultCard(previewRoot, {
      scope: "day-preview",
      name: ctx.dailyplan.name,
      kpis: previewWithAlloc,
      items: projectDailyPlanResultItems(
        ctx.dailyplan.meals,
        selectedMeal,
        {
          hour: hourInput?.value,
          note: noteInput?.value,
          editingDailyPlanMealId: isEdit() ? ctx.editing.dailyplanmeal_id : null,
        },
      ),
      emptyLabel: "Sin comidas",
    });

    previewBox.style.display = "flex";
  }

  // ---------------------------
  // Events
  // ---------------------------

  input.addEventListener("focus", () => {
    openList();
    renderMealList(browseMeals);
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

  hourInput?.addEventListener("input", showPreview);
  noteInput?.addEventListener("input", showPreview);

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
        detail: { sectionId: "dailyplan-picker-section", step: "impact" }
      }));

      enterEditMode();
      applySelectedMeal(meal);

      closeList();
    });
  });

  // ---------------------------
  // CANCEL EDIT
  // ---------------------------

  function cancelPicker() {
    clearSelection();
    enterAddMode();
    closeList();

    document.dispatchEvent(new CustomEvent("picker:close", {
      detail: { sectionId: "dailyplan-picker-section" }
    }));
  }

  if (btnCancel) {
    btnCancel.addEventListener("click", cancelPicker);
  }

  if (btnCancelInline) {
    btnCancelInline.addEventListener("click", cancelPicker);
  }

  document.addEventListener("picker:dismiss", event => {
    if (event.detail?.sectionId !== "dailyplan-picker-section") return;
    event.preventDefault();
    cancelPicker();
  });

  // ---------------------------
  // INITIAL MEAL FROM URL
  // ---------------------------

  const initialMealId = window.dailyplanInitialMeal;

  if (initialMealId) {
    const meal = findMealById(initialMealId);

    if (meal) {
      applySelectedMeal(meal);

      window.requestAnimationFrame(() => {
        document.dispatchEvent(new CustomEvent("picker:open", {
          detail: { sectionId: "dailyplan-picker-section", step: "impact" }
        }));
      });

      closeList();

      const url = new URL(window.location);
      url.searchParams.delete("select_meal");
      window.history.replaceState({}, "", url);
    }
  }
});
