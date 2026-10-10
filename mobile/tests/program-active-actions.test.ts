import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(file: string) {
  return readFile(path.resolve(process.cwd(), file), "utf8");
}

test("current program actions live in the header ellipsis sheet", async () => {
  const screen = await source("src/app/program/index.tsx");
  const actions = await source("src/components/programs/program-active-actions.tsx");
  const navigation = await source("src/components/navigation/app-navigation.tsx");

  assert.match(screen, /action: loading && !program \? undefined/);
  assert.match(screen, /<ProgramActiveActions/);
  assert.doesNotMatch(screen, /<Button label="Pausar programa"/);
  assert.doesNotMatch(screen, /calendarizations\/history/);
  assert.match(screen, /<CalendarizedProgramPlanning[\s\S]*<Button label="Cancelar programa" onPress=\{requestCancel\} variant="danger" \/>/);
  assert.match(screen, /initialAction=\{cancelRequested \? "cancel" : undefined\}/);
  assert.match(screen, /cancelAction: \{ marginTop: 28 \}/);
  assert.match(actions, /useState<ConfirmableAction \| null>\(initialAction \?\? null\)/);

  for (const label of [
    "Ver información del elemento",
    "Configurar recordatorios",
    "Ver programa original",
    "Ver historial de programas",
    "Cancelar programa",
  ]) {
    assert.match(actions, new RegExp(label));
  }
  assert.doesNotMatch(actions, /Cambiar de programa|Pausar programa|Reanudar programa/);
  const informationIndex = actions.indexOf('label="Ver información del elemento"');
  const remindersIndex = actions.indexOf('label="Configurar recordatorios"');
  const originalIndex = actions.indexOf('label="Ver programa original"');
  const historyIndex = actions.indexOf('label="Ver historial de programas"');
  const cancelIndex = actions.indexOf('label="Cancelar programa"');
  assert.ok(informationIndex < remindersIndex && remindersIndex < originalIndex && originalIndex < historyIndex && historyIndex < cancelIndex);
  assert.match(actions, /<ActionSheetModal/);
  assert.match(navigation, /headerPresentation\.mode === "default" && \(headerPresentation\.createAction \|\| headerPresentation\.action\)/);
  assert.match(navigation, /<MoreHorizontal/);
});

test("program history is a separate back-navigable card view", async () => {
  const history = await source("src/app/program/history.tsx");

  assert.match(history, /calendarizations\/history\?limit=50/);
  assert.match(history, /fallback: "\/program", mode: "back", title: "Historial de programas"/);
  assert.match(history, /<EntityCard/);
  assert.match(history, /eyebrow="Programa anterior"/);
  assert.match(history, /días con plan/);
});
