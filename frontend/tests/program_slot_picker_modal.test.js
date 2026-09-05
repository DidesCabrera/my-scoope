import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { projectProgramWeekRows } from "../../notas/static/notas/js/program_slot_projection.js";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

async function source(relativePath) {
  return readFile(path.join(repositoryRoot, relativePath), "utf8");
}

test("Program DailyPlan picker uses the shared two-step modal contract", async () => {
  const [template, controller, styles] = await Promise.all([
    source("notas/templates/components/program_slot_global_picker.html"),
    source("notas/static/notas/js/program_slot_picker.js"),
    source("notas/static/notas/css/components/program_slot_picker_modal.css"),
  ]);

  assert.match(template, /<dialog[\s\S]*id="program-slot-picker-section"[\s\S]*data-picker-modal/);
  assert.match(template, /data-picker-step-panel="selection"/);
  assert.match(template, /1\. Selecciona un plan diario/);
  assert.match(template, /data-picker-step-panel="impact"/);
  assert.match(template, /2\. Configura y revisa el impacto/);
  assert.match(template, /composition-picker-fixed-configuration program-slot-picker__days/);
  assert.match(template, /program-slot-picker__projection js-program-slot-projection/);
  assert.match(template, /entity-heading card-title-comp program-slot-picker__projection-heading/);
  assert.match(template, /<p class="card-title-eyebrow">[\s\S]*Resultado proyectado[\s\S]*<h3 id="program-slot-projection-title"/);
  assert.doesNotMatch(template, /<h4 id="program-slot-projection-title"/);
  assert.match(template, /composition-picker-modal__footer program-slot-picker__actions/);
  assert.doesNotMatch(template, /class="program-slot-picker section_picker/);

  assert.match(controller, /projectProgramWeekRows/);
  assert.match(controller, /renderDailyplanPickerCard\(\{ name, kcal, protein, carbs, fat, ppk,/);
  assert.match(controller, /renderKpiRow\("Protein", protein, proteinAlloc, "protein", ppk\)/);
  assert.match(controller, /class="program-week-day-table__ppk-value">\$\{numeric\(row\.ppk\)\.toFixed\(1\)\}/);
  assert.match(controller, /renderWeekProjection\(\);\s*showImpactStep\(\);/);
  assert.match(controller, /renderWeekProjection\(\);[\s\S]*js-program-slot-day-checkbox/);
  assert.match(controller, /sectionId: "program-slot-picker-section"/);

  assert.match(styles, /\.program-slot-picker-modal \.program-slot-picker__results\s*{[\s\S]*align-content: start;[\s\S]*grid-auto-rows: max-content;/);
  assert.match(styles, /\.program-slot-picker-modal \.program-slot-picker__preview\s*{[\s\S]*padding: 17px var\(--desktop-padding-lats\) 14px;[\s\S]*border: 1px solid var\(--border-soft\);/);
  assert.match(styles, /\.program-slot-picker-modal \.program-slot-picker__projection-card\.picker-impact\s*{[\s\S]*padding: 17px var\(--desktop-padding-lats\) 14px;[\s\S]*border: 1px solid var\(--border-soft\);/);
  assert.doesNotMatch(styles, /--desktop-padding-(?:top|bottom)/);
});

test("week projection replaces selected days and recalculates comparison shares", () => {
  const rows = [
    {
      day_number: 1,
      day_name: "Lunes",
      dailyplan_name: "Plan anterior",
      has_plan: true,
      is_empty: false,
      total_kcal: 1000,
      protein: 50,
      carbs: 100,
      fat: 40,
      kcal_protein: 200,
      kcal_carbs: 400,
      kcal_fat: 400,
    },
    {
      day_number: 2,
      day_name: "Martes",
      dailyplan_name: "Sin plan asignado",
      has_plan: false,
      is_empty: true,
      total_kcal: 0,
      protein: 0,
      carbs: 0,
      fat: 0,
      kcal_protein: 0,
      kcal_carbs: 0,
      kcal_fat: 0,
    },
  ];
  const selectedPlan = {
    id: 9,
    name: "Plan proyectado",
    total_kcal: 2000,
    protein: 100,
    carbs: 200,
    fat: 80,
    kcal_protein: 400,
    kcal_carbs: 800,
    kcal_fat: 800,
    ppk: 1.25,
    alloc: { protein: 20, carbs: 40, fat: 40 },
  };

  const projected = projectProgramWeekRows(rows, selectedPlan, [1, 2]);

  assert.equal(projected[0].projected_label, "Reemplazo");
  assert.equal(projected[1].projected_label, "Por agregar");
  assert.equal(projected[1].dailyplan_name, "Plan proyectado");
  assert.equal(projected[1].is_empty, false);
  assert.equal(projected[0].kcal_share, 50);
  assert.equal(projected[1].kcal_share, 50);
  assert.equal(projected[0].alloc.protein, 50);
  assert.deepEqual(projected[1].kcal_distribution, selectedPlan.alloc);
});

test("week projection preserves unselected days", () => {
  const rows = [
    {
      day_number: 1,
      dailyplan_name: "Plan actual",
      has_plan: true,
      total_kcal: 1000,
      kcal_protein: 200,
      kcal_carbs: 400,
      kcal_fat: 400,
    },
    {
      day_number: 2,
      dailyplan_name: "Plan actual 2",
      has_plan: true,
      total_kcal: 500,
      kcal_protein: 100,
      kcal_carbs: 200,
      kcal_fat: 200,
    },
  ];

  const projected = projectProgramWeekRows(rows, {
    id: 2,
    name: "Plan nuevo",
    total_kcal: 2000,
    kcal_protein: 400,
    kcal_carbs: 800,
    kcal_fat: 800,
  }, [2]);

  assert.equal(projected[0].dailyplan_name, "Plan actual");
  assert.equal(projected[0].is_projected, false);
  assert.equal(projected[1].dailyplan_name, "Plan nuevo");
  assert.equal(projected[1].is_projected, true);
  assert.equal(projected[0].kcal_share, 1000 / 3000 * 100);
});
