import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { dailyWeightTrend, sortedWeightTrend } from "../src/components/ui/weight-trend-values";

test("weight trend orders valid measurements chronologically without mutating history", () => {
  const history = [
    { id: 3, measured_on: "2026-10-07", weight_kg: 84.2 },
    { id: 1, measured_on: "2026-10-01", weight_kg: 85.1 },
    { id: 2, measured_on: "2026-10-04", weight_kg: Number.NaN },
  ];

  assert.deepEqual(sortedWeightTrend(history).map((item) => item.id), [1, 3]);
  assert.deepEqual(history.map((item) => item.id), [3, 1, 2]);
});

test("weight trend fills consecutive days with weighted estimates and carries the latest weight forward", () => {
  const trend = dailyWeightTrend([
    { id: 1, measured_on: "2026-10-01", weight_kg: 80 },
    { id: 2, measured_on: "2026-10-05", weight_kg: 84 },
  ], "2026-10-07");

  assert.deepEqual(trend.map((item) => item.measured_on), [
    "2026-10-01",
    "2026-10-02",
    "2026-10-03",
    "2026-10-04",
    "2026-10-05",
    "2026-10-06",
    "2026-10-07",
  ]);
  assert.deepEqual(trend.map((item) => item.weight_kg), [80, 81, 82, 83, 84, 84, 84]);
  assert.deepEqual(trend.map((item) => item.estimated), [false, true, true, true, false, true, true]);
});

test("weight trend ignores an earlier through date and still includes the latest measurement", () => {
  const trend = dailyWeightTrend([
    { id: 1, measured_on: "2026-10-01", weight_kg: 80 },
    { id: 2, measured_on: "2026-10-03", weight_kg: 82 },
  ], "2026-09-30");

  assert.equal(trend.at(-1)?.measured_on, "2026-10-03");
  assert.equal(trend.at(-1)?.estimated, false);
});

test("weight trend and history use the standard card surface", async () => {
  const screen = await readFile(path.resolve(process.cwd(), "src/app/weight.tsx"), "utf8");
  assert.match(screen, /<Card accent=\{tokens\.color\.protein\}>\s*<CardHeader title="Registro de peso actual" \/>/);
  assert.match(screen, /Mídete en condiciones similares para que la tendencia sea comparable\./);
  assert.match(screen, /El registro de peso te permitirá visualizar su variación\./);
  assert.match(screen, /La variación de peso puede deberse a diferentes factores/);
  assert.match(screen, /Por eso te aconsejamos evaluar la tendencia en el mediano plazo/);
  assert.match(screen, /<SectionPageHeader countLabel="mediciones" section="weight" subtitle="El registro de peso te permitirá visualizar su variación\. Esto revelará tendencias en el mediano y largo plazo\." title="Registra tu peso" \/>\s*<Card accent=\{tokens\.color\.protein\}>/);
  assert.match(screen, /<InlineNotice>[\s\S]*La variación de peso puede deberse[\s\S]*\{"\\n\\n"\}[\s\S]*Por eso te aconsejamos evaluar la tendencia[\s\S]*<\/InlineNotice>/);
  assert.doesNotMatch(screen, /eyebrow="Mediciones"/);
  assert.match(screen, /setHeaderPresentation\(\{ fallback: "\/today", identityVisible: compactHeaderVisible, mode: "back", title: "Registra tu peso" \}\)/);
  assert.match(screen, /<Screen headerMode="preserve" onHeaderVisibilityChange=\{setCompactHeaderVisible\}>/);
  assert.match(screen, /<Card accent=\{tokens\.color\.protein\}>[\s\S]*?<\/Card>\s*<InlineNotice>\s*La variación de peso/);
  assert.doesNotMatch(screen, /weightIntroduction/);
  assert.doesNotMatch(screen, /Una cifra aislada no define tu progreso/);
  assert.match(screen, /<Card>\s*<CardHeader description=\{`\$\{items\.length\} registros`\} title="Tendencia de peso" \/>\s*<WeightTrendChart items=\{items\} \/>\s*<\/Card>/);
  assert.match(screen, /<Card>[\s\S]*<CardHeader[\s\S]*title="Pesos históricos"[\s\S]*<KeyValueTable items=\{items\.map/);
  assert.match(screen, /label: historyDateLabel\(item\)/);
  assert.match(screen, /value: `\$\{item\.weight_kg\.toFixed\(1\)\} kg`/);
  assert.match(screen, /label=\{`Peso actual · \$\{formatDate\(localDateValue\(\)\)\}`\}/);
  assert.match(screen, /<NativeDateTimeField label="Hora de medición \(Opcional\)" mode="time"/);
  assert.match(screen, /const payload: WeightInput = \{ comment: comment\.trim\(\), measured_on: localDateValue\(\), measured_time: measuredTime \|\| localTimeValue\(\), weight_kg: weight \}/);
  assert.doesNotMatch(screen, /Incluir hora|SystemSwitch/);
  assert.match(screen, /item\.measured_time\?\.slice\(0, 5\)/);
  assert.match(screen, /accessibilityLabel=\{historyEditing \? "Finalizar edición de pesos históricos" : "Editar pesos históricos"\}/);
  assert.match(screen, /accessibilityLabel="Agregar medición anterior"[\s\S]*<Plus color=\{tokens\.color\.textMain\}/);
  assert.match(screen, /historyEditing[\s\S]*<Check color=\{tokens\.color\.textMain\}[\s\S]*<Pencil color=\{tokens\.color\.textMain\}/);
  assert.match(screen, /accessory: historyEditing \? \([\s\S]*accessibilityLabel=\{`Editar peso del \$\{historyDateLabel\(item\)\}`\}[\s\S]*onPress=\{\(\) => openEdit\(item\)\}/);
  assert.doesNotMatch(screen, /swipeAction|ReanimatedSwipeable/);
  assert.match(screen, /<ActionSheetModal onRequestClose=\{closeEdit\} visible=\{historyFormMode != null\}>/);
  assert.match(screen, /Puedes ingresar una medición antigua que no registraste en el momento\./);
  assert.match(screen, /function openCreate\(\)[\s\S]*setEditValue\(""\)[\s\S]*setEditDate\(""\)[\s\S]*setEditTime\(""\)/);
  assert.match(screen, /defaultValue=\{historyFormMode === "create" \? profile\?\.current_weight_kg\?\.toString\(\) : undefined\}/);
  assert.match(screen, /label="Peso"[\s\S]*label="Fecha"[\s\S]*label="Hora \(Opcional\)"/);
  assert.match(screen, /historyFormMode === "edit"[\s\S]*`\/api\/v1\/weights\/\$\{editingItem\.id\}`[\s\S]*method: "PATCH"[\s\S]*method: "POST"/);
  assert.doesNotMatch(screen, /item\.source|"Inicio"|"Manual"/);
  assert.doesNotMatch(screen, /<Card muted>/);
});
