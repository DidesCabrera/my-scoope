import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { sortedWeightTrend } from "../src/components/ui/weight-trend-values";

test("weight trend orders valid measurements chronologically without mutating history", () => {
  const history = [
    { id: 3, measured_on: "2026-10-07", weight_kg: 84.2 },
    { id: 1, measured_on: "2026-10-01", weight_kg: 85.1 },
    { id: 2, measured_on: "2026-10-04", weight_kg: Number.NaN },
  ];

  assert.deepEqual(sortedWeightTrend(history).map((item) => item.id), [1, 3]);
  assert.deepEqual(history.map((item) => item.id), [3, 1, 2]);
});

test("weight trend and history use the standard card surface", async () => {
  const screen = await readFile(path.resolve(process.cwd(), "src/app/weight.tsx"), "utf8");
  assert.match(screen, /<Card accent=\{tokens\.color\.protein\}>\s*<CardHeader title="Registro de peso actual" \/>/);
  assert.match(screen, /Mídete en condiciones similares para que la tendencia sea comparable\./);
  assert.match(screen, /El registro de peso te permitirá visualizar su variación\./);
  assert.match(screen, /La variación de peso puede deberse a diferentes factores/);
  assert.match(screen, /Por eso te aconsejamos evaluar la tendencia en el mediano plazo/);
  assert.match(screen, /<SectionPageHeader countLabel="mediciones" section="weight" title="Registra tu peso" \/>\s*<View style=\{styles\.weightIntroduction\}>[\s\S]*?<Text style=\{textStyles\.body\}>El registro/);
  assert.match(screen, /<InlineNotice>[\s\S]*La variación de peso puede deberse[\s\S]*\{"\\n\\n"\}[\s\S]*Por eso te aconsejamos evaluar la tendencia[\s\S]*<\/InlineNotice>/);
  assert.doesNotMatch(screen, /eyebrow="Mediciones"/);
  assert.match(screen, /setHeaderPresentation\(\{ fallback: "\/today", identityVisible: compactHeaderVisible, mode: "back", title: "Registra tu peso" \}\)/);
  assert.match(screen, /<Screen headerMode="preserve" onHeaderVisibilityChange=\{setCompactHeaderVisible\}>/);
  assert.doesNotMatch(screen, /<CardHeader title="Registro de peso actual" \/>\s*<View style=\{styles\.weightIntroduction\}>/);
  assert.match(screen, /weightIntroduction: \{ gap: tokens\.spacing\.sm \}/);
  assert.doesNotMatch(screen, /Una cifra aislada no define tu progreso/);
  assert.match(screen, /<Card>\s*<CardHeader description=\{`\$\{items\.length\} registros`\} title="Tendencia de peso" \/>\s*<WeightTrendChart items=\{items\} \/>\s*<\/Card>/);
  assert.match(screen, /<Card>[\s\S]*<CardHeader[\s\S]*title="Pesos históricos"[\s\S]*<KeyValueTable items=\{items\.map/);
  assert.match(screen, /label: historyDateLabel\(item\)/);
  assert.match(screen, /value: `\$\{item\.weight_kg\.toFixed\(1\)\} kg`/);
  assert.match(screen, /label=\{`Peso actual · \$\{formatDate\(localDateValue\(\)\)\}`\}/);
  assert.match(screen, /<NativeDateTimeField label="Hora de medición \(Opcional\)" mode="time"/);
  assert.doesNotMatch(screen, /Incluir hora|SystemSwitch/);
  assert.match(screen, /const payload: WeightInput = \{ measured_on: localDateValue\(\), measured_time: measuredTime \|\| null, weight_kg: weight \}/);
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
