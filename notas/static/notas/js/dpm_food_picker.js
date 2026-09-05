// ======================================================
// dpm_food_picker.js
// Picker DPM Food
// ======================================================

import {
  portionFromFood,
  previewTotals,
  removePortionTotals,
  computePPK,
  computeAlloc
} from "./dpm_food_math.js";

import {
  renderBase,
  renderPortion
} from "./dpm_food_preview.js";

import { renderFoodItem } from "./food_item_list.js";
import {
  projectDailyPlanResultItems,
  projectMealResultItems,
  renderResultCard
} from "./picker_result_card.js";

document.addEventListener("DOMContentLoaded", () => {

  const ctx = window.FOOD_PICKER_CONTEXT;
  let foods = Array.isArray(window.FOOD_PICKER_FOODS)
    ? window.FOOD_PICKER_FOODS
    : [];

  const foodSearchCache = new Map();
  let activeSearchController = null;
  let searchDebounceTimer = null;
  let initialFoodsLoaded = foods.length > 0;

  foods.forEach(food => {
    if (food?.id) {
      foodSearchCache.set(Number(food.id), food);
    }
  });

  const picker = document.getElementById("food-picker");
  if (!picker) return;

  // ---------------------------
  // DOM
  // ---------------------------
  const input = document.getElementById("food-search");
  const list = document.getElementById("food-list");
  const preview = document.getElementById("food-preview");
  const quantityInput = document.getElementById("food-quantity");

  const form = document.getElementById("form-preview");

  const title = document.getElementById("dpm-food-form-title");
  const modal = document.getElementById("dpm-picker-section");
  const addHeaderIcon = modal?.querySelector('[data-picker-header-icon="add"]');
  const editHeaderIcon = modal?.querySelector('[data-picker-header-icon="edit"]');

  const btnAdd = document.getElementById("btn-add-food");
  const btnUpdate = document.getElementById("btn-update-food");
  const btnCancel = document.getElementById("btn-cancel-edit");
  const btnCancelInline = document.getElementById("btn-cancel-picker-inline-dpm");

  const hiddenFoodId = document.getElementById("selected-food-id");
  const hiddenQuantity = document.getElementById("selected-food-quantity");

  const hiddenPickerMode = document.getElementById("food-picker-mode");
  const hiddenEditingMealfoodId = document.getElementById("editing-mealfood-id");
  const hiddenEditingOriginalQuantity = document.getElementById("editing-original-quantity");

  let selectedFood = null;

  // ---------------------------
  // Helpers
  // ---------------------------
  function isEdit() {
    return ctx.mode === "edit";
  }

  function syncHeaderMode(mode) {
    const editing = mode === "edit";
    if (addHeaderIcon) addHeaderIcon.hidden = editing;
    if (editHeaderIcon) editHeaderIcon.hidden = !editing;
  }

  function showImpactStep() {
    document.dispatchEvent(new CustomEvent("picker:step", {
      detail: { sectionId: "dpm-picker-section", step: "impact" }
    }));
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

  function findFoodById(foodId) {
    return foodSearchCache.get(Number(foodId)) || null;
  }

  function cacheFoodResults(results) {
    if (!Array.isArray(results)) return;

    results.forEach(food => {
      if (food?.id) {
        foodSearchCache.set(Number(food.id), food);
      }
    });
  }

  function getCachedFoodResults() {
    return Array.from(foodSearchCache.values());
  }

  function getFoodDisplayName(food) {
    return food?.display_name || food?.name || "";
  }

  function normalizeSearchValue(value) {
    return String(value ?? "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }

  function getFoodSearchText(food) {
    return normalizeSearchValue(
      food?.search_text || food?.display_name || food?.name || ""
    );
  }

  function filterFoodsBySearch(value) {
    const normalizedValue = normalizeSearchValue(value);
    const cachedFoods = getCachedFoodResults();

    if (!normalizedValue) {
      return cachedFoods;
    }

    return cachedFoods.filter(food => {
      return getFoodSearchText(food).includes(normalizedValue);
    });
  }

  function getFoodSearchUrl(value, limit = 50) {
    const params = new URLSearchParams();
    params.set("search", value);
    params.set("limit", String(limit));

    return `/app/api/foods/?${params.toString()}`;
  }

  function getFoodByIdUrl(foodId) {
    const params = new URLSearchParams();
    params.set("food_id", String(foodId));
    params.set("limit", "1");

    return `/app/api/foods/?${params.toString()}`;
  }

  async function fetchFoods(url, signal = undefined) {
    const response = await fetch(url, {
      headers: {
        "Accept": "application/json"
      },
      signal
    });

    if (!response.ok) {
      return [];
    }

    const results = await response.json();

    if (!Array.isArray(results)) {
      return [];
    }

    cacheFoodResults(results);

    return results;
  }

  async function getInitialFoodResults() {
    if (initialFoodsLoaded) {
      return foods;
    }

    const results = await fetchFoods(getFoodSearchUrl("", 50));
    foods = results;
    initialFoodsLoaded = true;

    return foods;
  }

  async function fetchFoodById(foodId) {
    const cachedFood = findFoodById(foodId);

    if (cachedFood) {
      return cachedFood;
    }

    try {
      const results = await fetchFoods(getFoodByIdUrl(foodId));
      const fetchedFood = results[0] || null;

      if (fetchedFood) {
        return fetchedFood;
      }
    } catch (error) {
      // Keep edit mode usable even if the single-food endpoint fails.
    }

    await getInitialFoodResults();

    return findFoodById(foodId);
  }

  async function searchFoodsFromServer(value) {
    const normalizedValue = normalizeSearchValue(value);

    if (!normalizedValue) {
      return getInitialFoodResults();
    }

    if (activeSearchController) {
      activeSearchController.abort();
    }

    activeSearchController = new AbortController();

    const results = await fetchFoods(
      getFoodSearchUrl(value, 50),
      activeSearchController.signal
    );

    return results.length ? results : filterFoodsBySearch(value);
  }

  function scheduleServerSearch(value) {
    window.clearTimeout(searchDebounceTimer);

    searchDebounceTimer = window.setTimeout(async () => {
      try {
        const results = await searchFoodsFromServer(value);
        renderFoodList(results);
        openList();
      } catch (error) {
        if (error.name === "AbortError") {
          return;
        }

        renderFoodList(filterFoodsBySearch(value));
        openList();
      }
    }, 180);
  }

  function syncHiddenState() {
    if (hiddenPickerMode) {
      hiddenPickerMode.value = ctx.mode || "add";
    }

    if (ctx.editing) {
      if (hiddenEditingMealfoodId) {
        hiddenEditingMealfoodId.value = String(ctx.editing.mealfood_id ?? "");
      }
      if (hiddenEditingOriginalQuantity) {
        hiddenEditingOriginalQuantity.value = String(ctx.editing.original_quantity ?? "");
      }
    } else {
      if (hiddenEditingMealfoodId) {
        hiddenEditingMealfoodId.value = "";
      }
      if (hiddenEditingOriginalQuantity) {
        hiddenEditingOriginalQuantity.value = "";
      }
    }
  }

  function setAddMode() {
    ctx.mode = "add";
    ctx.editing = null;

    title.textContent = "Agrega un Alimento";
    syncHeaderMode("add");
    btnAdd.style.display = "inline-block";
    btnUpdate.style.display = "none";
    btnCancel.style.display = "inline-block";

    form.action = form.dataset.defaultAction || form.action;

    syncHiddenState();
  }

  function setEditMode({ mealfoodId, foodId, originalQuantity, updateUrl }) {
    ctx.mode = "edit";
    ctx.editing = {
      mealfood_id: Number(mealfoodId),
      food_id: Number(foodId),
      original_quantity: Number(originalQuantity)
    };

    title.textContent = "Edita el Alimento";
    syncHeaderMode("edit");
    btnAdd.style.display = "none";
    btnUpdate.style.display = "inline-block";
    btnCancel.style.display = "inline-block";

    form.action = updateUrl;

    syncHiddenState();
  }

  function resetPickerState() {
    selectedFood = null;

    hiddenFoodId.value = "";
    hiddenQuantity.value = "";

    input.value = "";
    quantityInput.value = "100";

    preview.style.display = "none";

    closeList();
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
  // Food list
  // ---------------------------
  function renderFoodList(items) {
    list.innerHTML = "";
  
    items.forEach(food => {
      if (!food || !food.name) return;
  
      const li = document.createElement("li");
      li.className = "picker-list-item food-item";
      li.innerHTML = renderFoodItem(food);
  
      li.addEventListener("click", () => {
        selectedFood = food;
        input.value = getFoodDisplayName(food);
  
        closeList();
        showPreview();
        showImpactStep();
      });
  
      list.appendChild(li);
    });
  
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  }


  function normalizeSourceLabel(source) {
    if (!source) return "";

    const normalized = String(source).toLowerCase();

    if (normalized === "usda") return "USDA";
    if (normalized === "open_food_facts") return "Open Food Facts";
    if (normalized === "latinfoods") return "LATINFOODS";
    if (normalized === "inta_chile") return "INTA Chile";
    if (normalized === "manual") return "Manual";
    if (normalized === "global") return "Global";
    if (normalized === "system") return "Sistema";
    if (normalized === "user") return "Usuario";

    return String(source)
      .replaceAll("_", " ")
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  function renderSelectedFoodSource(food) {
    const sourceNode = document.querySelector('[data-scope="food-preview"] [data-role="food-source"]');
    if (!sourceNode) return;

    const sourceLabel = normalizeSourceLabel(food?.source);
    sourceNode.textContent = sourceLabel;
    sourceNode.hidden = !sourceLabel;
  }

  // ---------------------------
  // Preview
  // ---------------------------
  function showPreview() {
    if (!selectedFood) return;

    preview.style.display = "flex";
    document.getElementById("preview-name").textContent = getFoodDisplayName(selectedFood);
    renderSelectedFoodSource(selectedFood);

    hiddenFoodId.value = selectedFood.id;

    renderBase(selectedFood);

    quantityInput.value = isEdit()
      ? String(ctx.editing.original_quantity)
      : "100";

    updateQuantity();
  }

  function updateQuantity() {
    if (!selectedFood) return;

    const rawQuantity = Number(quantityInput.value);
    const quantity = !rawQuantity || rawQuantity <= 0 ? 0 : rawQuantity;

    hiddenQuantity.value = String(quantity);

    // -------- FOOD PORTION --------
    const newPortion = portionFromFood(selectedFood, quantity);
    renderPortion(newPortion);

    // -------- MEAL BASE --------
    let baseMeal = ctx.meal.kpis;

    if (isEdit()) {
      const originalFood = findFoodById(ctx.editing.food_id);
      const oldPortion = originalFood
        ? portionFromFood(originalFood, ctx.editing.original_quantity)
        : null;

      baseMeal = removePortionTotals(ctx.meal.kpis, oldPortion);
    }

    const previewMeal = previewTotals(baseMeal, newPortion);

    const mealWeight = ctx.meal?.kpis?.weight;
    previewMeal.ppk = computePPK(previewMeal.protein, mealWeight);
    previewMeal.alloc = computeAlloc(previewMeal);

    const projectedMealFoods = projectMealResultItems(
      ctx.meal.foods,
      selectedFood,
      quantity,
      isEdit() ? ctx.editing.mealfood_id : null,
    );

    renderResultCard(preview, {
      scope: "dpm-meal-result",
      name: ctx.meal.name,
      owner: ctx.meal.owner,
      kpis: previewMeal,
      items: projectedMealFoods,
      entityKind: "meal",
    });

    // -------- DAILYPLAN BASE --------
    let baseDailyPlan = ctx.dailyplan.kpis;

    if (isEdit()) {
      const originalFood = findFoodById(ctx.editing.food_id);
      const oldPortion = originalFood
        ? portionFromFood(originalFood, ctx.editing.original_quantity)
        : null;

      baseDailyPlan = removePortionTotals(
        ctx.dailyplan.kpis,
        oldPortion
      );
    }

    const previewDailyPlan = previewTotals(baseDailyPlan, newPortion);

    const dailyPlanWeight = ctx.dailyplan?.kpis?.weight;
    previewDailyPlan.ppk = computePPK(previewDailyPlan.protein, dailyPlanWeight);
    previewDailyPlan.alloc = computeAlloc(previewDailyPlan);

    const projectedMeal = {
      id: ctx.meal.id,
      name: ctx.meal.name,
      ...previewMeal,
      foods: projectedMealFoods,
    };

    renderResultCard(preview, {
      scope: "dpm-dailyplan-result",
      name: ctx.dailyplan.name,
      owner: ctx.dailyplan.owner,
      kpis: previewDailyPlan,
      items: projectDailyPlanResultItems(
        ctx.dailyplan.meals,
        projectedMeal,
        {
          hour: ctx.dpm?.hour,
          note: ctx.dpm?.note,
          editingDailyPlanMealId: ctx.dpm?.id,
        },
      ),
      entityKind: "dailyplan",
    });
  }

  // ---------------------------
  // Input events
  // ---------------------------
  input.addEventListener("focus", async () => {
    renderFoodList(await getInitialFoodResults());
    openList();
  });

  input.addEventListener("input", () => {
    const value = input.value;

    if (!normalizeSearchValue(value)) {
      getInitialFoodResults().then(results => {
        renderFoodList(results);
        openList();
      });
      return;
    }

    renderFoodList(filterFoodsBySearch(value));
    openList();

    scheduleServerSearch(value);
  });

  quantityInput.addEventListener("input", updateQuantity);

  document.addEventListener("mousedown", event => {
    if (!picker.contains(event.target)) {
      closeList();
    }
  });

  // ---------------------------
  // Edit mode
  // ---------------------------
  document.querySelectorAll(".edit-food-btn").forEach(button => {
    button.addEventListener("click", () => {
      setEditMode({
        mealfoodId: button.dataset.id,
        foodId: button.dataset.foodId,
        originalQuantity: button.dataset.qty,
        updateUrl: button.dataset.updateUrl
      });

      document.dispatchEvent(new CustomEvent("picker:open", {
        detail: { sectionId: "dpm-picker-section", step: "impact" }
      }));

      input.value = button.dataset.name || "";
      quantityInput.value = button.dataset.qty || "100";

      fetchFoodById(ctx.editing.food_id).then(food => {
        selectedFood = food;
        if (!selectedFood) return;

        input.value = getFoodDisplayName(selectedFood);
        showPreview();
      });
    });
  });

  // ---------------------------
  // Cancel
  // ---------------------------
  btnCancel.addEventListener("click", () => {
    setAddMode();
    resetPickerState();

    document.dispatchEvent(new CustomEvent("picker:close", {
      detail: { sectionId: "dpm-picker-section" }
    }));
  });

  if (btnCancelInline) {
    btnCancelInline.addEventListener("click", () => {
      setAddMode();
      resetPickerState();

      document.dispatchEvent(new CustomEvent("picker:close", {
        detail: { sectionId: "dpm-picker-section" }
      }));
    });
  }

  document.addEventListener("picker:dismiss", event => {
    if (event.detail?.sectionId !== "dpm-picker-section") return;
    event.preventDefault();
    setAddMode();
    resetPickerState();

    document.dispatchEvent(new CustomEvent("picker:close", {
      detail: { sectionId: "dpm-picker-section" }
    }));
  });

  // ---------------------------
  // Init
  // ---------------------------
  if (!form.dataset.defaultAction) {
    form.dataset.defaultAction = form.action;
  }

  syncHiddenState();

  const initialFoodId = window.DPM_FOOD_PICKER_INITIAL_ID;
  if (initialFoodId) {
    setAddMode();
    fetchFoodById(initialFoodId).then(food => {
      if (!food) return;

      selectedFood = food;
      input.value = getFoodDisplayName(food);
      showPreview();

      document.dispatchEvent(new CustomEvent("picker:open", {
        detail: { sectionId: "dpm-picker-section", step: "impact" }
      }));

      const url = new URL(window.location);
      url.searchParams.delete("select_food");
      window.history.replaceState({}, "", url);
    });
  }
});
