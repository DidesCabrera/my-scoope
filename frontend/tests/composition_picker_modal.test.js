import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const repositoryRoot = path.resolve(import.meta.dirname, "../..");

async function source(relativePath) {
  return readFile(path.join(repositoryRoot, relativePath), "utf8");
}

test("Food and Meal web pickers share the two-step top-layer dialog contract", async () => {
  const [food, meal] = await Promise.all([
    source("notas/templates/components/picker_block_food.html"),
    source("notas/templates/components/picker_block_meal.html"),
  ]);

  for (const template of [food, meal]) {
    assert.match(template, /<dialog[\s\S]*data-picker-modal/);
    assert.match(template, /data-picker-step="selection"/);
    assert.match(template, /data-picker-step-panel="selection"/);
    assert.match(template, /data-picker-step-panel="impact"/);
    assert.match(template, /data-picker-go-to="selection"/);
    assert.match(template, /data-picker-dismiss/);
    assert.doesNotMatch(template, /composition-picker-modal__eyebrow/);
    assert.doesNotMatch(template, /composition-picker-steps/);
    assert.doesNotMatch(template, /composition-picker-step-heading[\s\S]*?<p>/);
    assert.match(template, /composition-picker-step-heading[\s\S]*?composition-picker-entry-actions[\s\S]*?composition-picker-search-row[\s\S]*?selector-list/);
    assert.equal((template.match(/class="composition-picker-modal__body(?:\s|\")/g) || []).length, 2);
    assert.equal((template.match(/class="composition-picker-modal__footer"/g) || []).length, 2);
    assert.match(template, /composition-picker-modal__body[\s\S]*?composition-picker-modal__footer/);
    assert.match(template, /composition-picker-modal__action--secondary/);
    assert.match(template, /composition-picker-modal__action--primary/);
    assert.doesNotMatch(template, /class="section_picker/);
    assert.match(template, /data-picker-header-icon="add"[\s\S]*?data-lucide="plus"/);
    assert.match(template, /data-picker-header-icon="edit"[\s\S]*?data-lucide="repeat"/);
    assert.match(template, /<h3[^>]*>1\. Selecciona/);
    assert.match(template, /<h3>2\. Configura y revisa el impacto<\/h3>/);
  }

  assert.match(food, /url 'food_create'[\s\S]*return_to=/);
  assert.match(food, />\s*Crear alimento\s*</);
  assert.match(food, /entity-card card picker-selection-card picker-section picker-food-info/);
  assert.match(food, /card_picker_result\.html[\s\S]*result_scope="meal-result"/);
  assert.doesNotMatch(food, /grid_picker_food_preview|class="preview-picker"/);
  assert.match(meal, /url 'create_meal_for_dailyplan'/);
  assert.match(meal, />\s*Crear comida\s*</);
  assert.match(meal, /entity-card card picker-selection-card[\s\S]*?picker-meal-info[\s\S]*?composition-picker-schedule-fields[\s\S]*?<\/section>[\s\S]*?picker-impact/);
  assert.match(meal, /card_picker_result\.html[\s\S]*result_scope="day-preview"/);
  assert.match(meal, /data-role="edit-selected-meal"[\s\S]*?Editar comida/);
  assert.doesNotMatch(meal, /grid_picker_meal_day_preview|class="preview-picker"/);
});

test("composition picker keeps padding on scroll content and actions in a fixed footer", async () => {
  const styles = await source("notas/static/notas/css/components/composition_picker_modal.css");

  assert.match(styles, /\.composition-picker-modal\s*\{[\s\S]*?background:\s*var\(--surface-card\);/);
  assert.match(styles, /\.composition-picker-modal__body\s*\{[\s\S]*?overflow-y:\s*auto;[\s\S]*?padding:\s*0 24px 22px;/);
  assert.match(styles, /\.composition-picker-modal__footer\s*\{[\s\S]*?flex:\s*0 0 auto;[\s\S]*?background:\s*var\(--surface-card\);[\s\S]*?border-top:/);
  assert.match(styles, /\.composition-picker-step-heading--impact\s*\{[\s\S]*?align-items:\s*center;[\s\S]*?justify-content:\s*space-between;/);
});

test("impact cards reuse UI-system card, KPI, tab, and data-grid contracts", async () => {
  const resultCard = await source("notas/templates/components/card_picker_result.html");

  assert.match(resultCard, /entity-card card picker-result-card/);
  assert.match(resultCard, /entity-heading card-title-comp/);
  assert.match(resultCard, /dash-kpi-comp/);
  assert.match(resultCard, /detail_tabs_foods\.html/);
  assert.match(resultCard, /detail_tabs_meals\.html/);
  assert.match(resultCard, /data-grid--foods/);
  assert.match(resultCard, /data-grid--meals/);
  assert.match(resultCard, /data-grid--mobile-foods-alloc/);
  assert.match(resultCard, /data-grid--mobile-alloc/);
});

test("selected Food and Meal summaries use the entity-card main structure", async () => {
  const [food, meal, mealPreview] = await Promise.all([
    source("notas/templates/components/card_picker_food.html"),
    source("notas/templates/components/card_picker_meal.html"),
    source("notas/static/notas/js/meal_preview.js"),
  ]);

  for (const summary of [food, meal]) {
    assert.match(
      summary,
      /picker-summary-card--selected[\s\S]*?entity-card__main card-main[\s\S]*?entity-card__title card-title[\s\S]*?entity-card__kpi card-kpi/,
    );
    assert.match(summary, /entity-heading card-title-comp/);
  }

  assert.match(food, /card-title-eyebrow[\s\S]*?Alimento seleccionado[\s\S]*?<h3[^>]*data-role="preview-name"/);
  assert.match(food, /card-title-badges[\s\S]*?data-role="food-source"[\s\S]*?100g/);
  assert.match(meal, /card-title-eyebrow[\s\S]*?Comida seleccionada[\s\S]*?<h3[^>]*data-role="preview-name"/);
  assert.match(meal, /entity-indicators structural-indicators[\s\S]*?data-role="selected-food-count"/);
  assert.match(mealPreview, /selected-food-count[\s\S]*?normalizedFoods\.length/);
});

test("impact keeps a stable dialog height and scrolls only its stacked picker layout", async () => {
  const styles = await source("notas/static/notas/css/components/composition_picker_modal.css");

  assert.match(styles, /\.composition-picker-modal\s*\{[\s\S]*?height:\s*min\(820px, calc\(100dvh - 32px\)\);/);
  assert.match(styles, /\.composition-picker-modal__body--impact\s*\{[\s\S]*?overflow:\s*hidden;/);
  assert.match(styles, /\.composition-picker-modal \.picker-layout\s*\{[\s\S]*?flex-direction:\s*column;[\s\S]*?overflow-y:\s*auto;/);
  assert.match(styles, /\.composition-picker-modal \.picker-layout\s*\{[\s\S]*?padding:\s*0;[\s\S]*?background:\s*transparent;[\s\S]*?border:\s*0;[\s\S]*?border-radius:\s*0;/);
  assert.match(styles, /\.composition-picker-modal \.picker-selection-card\s*\{/);
  assert.match(styles, /\.composition-picker-modal \.selector > \.selector-list\s*\{[\s\S]*?width:\s*100%;[\s\S]*?border:\s*0;[\s\S]*?border-radius:\s*0;/);
});

test("selection keeps heading controls fixed and scrolls only the result list", async () => {
  const styles = await source("notas/static/notas/css/components/composition_picker_modal.css");

  assert.match(styles, /\.composition-picker-modal__body--selection\s*\{[\s\S]*?overflow:\s*hidden;/);
  assert.match(styles, /\.composition-picker-modal \.selector\s*\{[\s\S]*?flex-direction:\s*column;[\s\S]*?min-height:\s*0;/);
  assert.match(styles, /\.composition-picker-modal \.selector > \.selector-list\s*\{[\s\S]*?flex:\s*1 1 auto;[\s\S]*?overflow-y:\s*auto;/);
});

test("shared picker controller owns modal lifecycle, steps, and accessible dismissal", async () => {
  const [controller, styles] = await Promise.all([
    source("notas/static/notas/js/picker_toggle.js"),
    source("notas/static/notas/css/components/composition_picker_modal.css"),
  ]);

  assert.match(controller, /section\.showModal\(\)/);
  assert.match(controller, /section\.close\(\)/);
  assert.match(controller, /event\.preventDefault\(\)[\s\S]*requestDismiss\(section\)/);
  assert.match(controller, /event\.target === section/);
  assert.match(controller, /picker:dismiss/);
  assert.match(controller, /picker:step/);
  assert.match(controller, /panel\.hidden = !isCurrent;[\s\S]*?panel\.style\.removeProperty\("display"\)/);
  assert.match(styles, /\.composition-picker-modal__step\[hidden\]\s*\{\s*display:\s*none !important;/);
  assert.match(controller, /has-picker-modal-open/);
  assert.match(controller, /focusTarget\?\.focus/);
});

test("selection advances to impact without changing the existing submit contracts", async () => {
  const [food, meal] = await Promise.all([
    source("notas/static/notas/js/food_picker.js"),
    source("notas/static/notas/js/meal_picker.js"),
  ]);

  assert.match(food, /sectionId: "meal-picker-section", step: "impact"/);
  assert.match(food, /syncHeaderMode\("add"\)/);
  assert.match(food, /syncHeaderMode\("edit"\)/);
  assert.match(food, /FOOD_PICKER_INITIAL_ID/);
  assert.match(food, /form\.action = updateUrl/);

  assert.match(meal, /sectionId: "dailyplan-picker-section", step: "impact"/);
  assert.match(meal, /syncHeaderMode\("add"\)/);
  assert.match(meal, /syncHeaderMode\("edit"\)/);
  assert.match(meal, /meal\?\.detail_url[\s\S]*?editSelectedMeal\.setAttribute\("href"/);
  assert.match(meal, /form\.action = ADD_ACTION/);
  assert.match(meal, /dailyplanmeal_id/);
});
