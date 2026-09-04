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
    assert.match(template, /composition-picker-search-row[\s\S]*?selector-list/);
    assert.doesNotMatch(template, /class="section_picker/);
  }

  assert.match(food, /url 'food_create'[\s\S]*return_to=/);
  assert.match(food, />\s*Crear alimento\s*</);
  assert.match(meal, /url 'create_meal_for_dailyplan'/);
  assert.match(meal, />\s*Crear comida\s*</);
});

test("shared picker controller owns modal lifecycle, steps, and accessible dismissal", async () => {
  const controller = await source("notas/static/notas/js/picker_toggle.js");

  assert.match(controller, /section\.showModal\(\)/);
  assert.match(controller, /section\.close\(\)/);
  assert.match(controller, /event\.preventDefault\(\)[\s\S]*requestDismiss\(section\)/);
  assert.match(controller, /event\.target === section/);
  assert.match(controller, /picker:dismiss/);
  assert.match(controller, /picker:step/);
  assert.match(controller, /has-picker-modal-open/);
  assert.match(controller, /focusTarget\?\.focus/);
});

test("selection advances to impact without changing the existing submit contracts", async () => {
  const [food, meal] = await Promise.all([
    source("notas/static/notas/js/food_picker.js"),
    source("notas/static/notas/js/meal_picker.js"),
  ]);

  assert.match(food, /sectionId: "meal-picker-section", step: "impact"/);
  assert.match(food, /FOOD_PICKER_INITIAL_ID/);
  assert.match(food, /form\.action = updateUrl/);

  assert.match(meal, /sectionId: "dailyplan-picker-section", step: "impact"/);
  assert.match(meal, /form\.action = ADD_ACTION/);
  assert.match(meal, /dailyplanmeal_id/);
});
