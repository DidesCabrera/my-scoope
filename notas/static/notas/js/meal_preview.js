// ======================================================
// Helpers
// ======================================================

function resolveScoped(container, scope, role, fallbackId) {

  const scopedRoot = container.querySelector(`[data-scope="${scope}"]`);

  if (scopedRoot) {
      return scopedRoot.querySelector(`[data-role="${role}"]`)
          || document.getElementById(fallbackId);
  }

  return document.getElementById(fallbackId);
}

function setAlloc(container, scope, role, textRole, fallbackCellId, fallbackTextId, value) {

    const cell = resolveScoped(container, scope, role, fallbackCellId);
    const text = resolveScoped(container, scope, textRole, fallbackTextId);
  
    if (cell) {
        cell.style.setProperty("--alloc", value.toFixed(0));
    }
  
    if (text) {
        text.textContent = value.toFixed(0) + "%";
    }
  }


// ======================================================
// Selected meal (TABLA 1)
// ======================================================

export function renderSelectedMeal(container, meal) {

  resolveScoped(container, "meal-preview", "preview-name", "dp-preview-name").textContent =
      meal.name;

  resolveScoped(container, "meal-preview", "meal-kcal", "dp-meal-kcal").textContent =
      meal.total_kcal.toFixed(0);

  resolveScoped(container, "meal-preview", "meal-protein", "dp-meal-protein").textContent =
      meal.protein.toFixed(0);

  resolveScoped(container, "meal-preview", "meal-carbs", "dp-meal-carbs").textContent =
      meal.carbs.toFixed(0);

  resolveScoped(container, "meal-preview", "meal-fat", "dp-meal-fat").textContent =
      meal.fat.toFixed(0);

 
  const alloc = meal.alloc;

  setAlloc(container, "meal-preview", "alloc-protein", "alloc-protein-text",
      "meal-alloc-protein-cell", "meal-alloc-protein-text", alloc.protein);

  setAlloc(container, "meal-preview", "alloc-carbs", "alloc-carbs-text",
      "meal-alloc-carbs-cell", "meal-alloc-carbs-text", alloc.carbs);

  setAlloc(container, "meal-preview", "alloc-fat", "alloc-fat-text",
      "meal-alloc-fat-cell", "meal-alloc-fat-text", alloc.fat);
}


// ======================================================
// Day preview (TABLA 2)
// ======================================================

export function renderDayPreview(container, current, preview, meal) {

    // MEAL IMPACT
    if (meal) {
  
      resolveScoped(container, "day-preview", "impact-meal-kcal", "dp-meal-kcal")
          .textContent = meal.total_kcal.toFixed(0);
  
      resolveScoped(container, "day-preview", "impact-meal-protein", "dp-meal-protein")
          .textContent = meal.protein.toFixed(0);
  
      resolveScoped(container, "day-preview", "impact-meal-carbs", "dp-meal-carbs")
          .textContent = meal.carbs.toFixed(0);
  
      resolveScoped(container, "day-preview", "impact-meal-fat", "dp-meal-fat")
          .textContent = meal.fat.toFixed(0);
    }
  
    // PREVIEW
    renderBlock(container, "day-preview", "prev", preview);
  }



/* ===================================================== */
/* Block Renderer */
/* ===================================================== */

function renderBlock(container, scope, prefix, data) {

  // Macros
  resolveScoped(container, scope, `${prefix}-kcal`, `${prefix === "cur" ? "dp-cur-kcal" : "dp-prev-kcal"}`)
      .textContent = data.total_kcal.toFixed(0);

  resolveScoped(container, scope, `${prefix}-protein`, `${prefix === "cur" ? "dp-cur-protein" : "dp-prev-protein"}`)
      .textContent = data.protein.toFixed(0);

  resolveScoped(container, scope, `${prefix}-carbs`, `${prefix === "cur" ? "dp-cur-carbs" : "dp-prev-carbs"}`)
      .textContent = data.carbs.toFixed(0);

  resolveScoped(container, scope, `${prefix}-fat`, `${prefix === "cur" ? "dp-cur-fat" : "dp-prev-fat"}`)
      .textContent = data.fat.toFixed(0);


  // Allocations
  setAlloc(
      container,
      scope,
      `${prefix}-alloc-protein`,
      `${prefix}-alloc-protein-text`,
      `${prefix === "cur" ? "dp-cur-alloc-protein-cell" : "dp-prev-alloc-protein-cell"}`,
      `${prefix === "cur" ? "dp-cur-alloc-protein-text" : "dp-prev-alloc-protein-text"}`,
      data.alloc.protein
  );

  setAlloc(
      container,
      scope,
      `${prefix}-alloc-carbs`,
      `${prefix}-alloc-carbs-text`,
      `${prefix === "cur" ? "dp-cur-alloc-carbs-cell" : "dp-prev-alloc-carbs-cell"}`,
      `${prefix === "cur" ? "dp-cur-alloc-carbs-text" : "dp-prev-alloc-carbs-text"}`,
      data.alloc.carbs
  );

  setAlloc(
      container,
      scope,
      `${prefix}-alloc-fat`,
      `${prefix}-alloc-fat-text`,
      `${prefix === "cur" ? "dp-cur-alloc-fat-cell" : "dp-prev-alloc-fat-cell"}`,
      `${prefix === "cur" ? "dp-cur-alloc-fat-text" : "dp-prev-alloc-fat-text"}`,
      data.alloc.fat
  );

  const ppkNode = resolveScoped(container, scope, `${prefix}-ppk`, null);

    if (ppkNode) {
        ppkNode.textContent = `${data.ppk.toFixed(1)}g/kg`;
    }

}


export function renderFoodsAggregation(container, foods) {

  const scope = container.querySelector('[data-role="foods-aggregation"]');
  if (!scope) return;

  scope.innerHTML = "";

  if (!foods || !foods.length) {
      scope.innerHTML = "<span>No foods</span>";
      return;
  }

  const line = foods
      .map(food => `${food.name} (${food.grams}g)`)
      .join(", ");

  scope.innerHTML = `<span class="foods-inline">${line}</span>`;
}


