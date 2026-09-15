import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string): Promise<string> {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("editable food and meal panel rows expose native swipe actions on every data tab", async () => {
  const panels = await source("src/components/panels/entity-panels.tsx");

  assert.match(panels, /ReanimatedSwipeable/);
  assert.match(panels, /label="Editar"/);
  assert.match(panels, /label="Reemplazar"/);
  assert.match(panels, /label="Eliminar"/);
  assert.match(panels, /accessibilityHint="Desliza hacia la izquierda para ver acciones/);

  for (const tab of ["quantity", "calories", "macros", "distribution", "allocation"]) {
    assert.match(panels, new RegExp(`activeTab === "${tab}"[\\s\\S]*?editing=\\{rowEditing\\}`));
  }
  for (const tab of ["menu", "calories", "macros", "distribution", "allocation"]) {
    assert.match(panels, new RegExp(`activeTab === "${tab}"[\\s\\S]*?editing=\\{rowEditing\\}`));
  }
});

test("editable rows reorder after a deliberate long press and persist on drop", async () => {
  const panels = await source("src/components/panels/entity-panels.tsx");
  const layout = await source("src/app/_layout.tsx");

  assert.match(layout, /GestureHandlerRootView style=\{styles\.gestureRoot\}/);
  assert.match(panels, /Gesture\.LongPress\(\)\.minDuration\(320\)/);
  assert.match(panels, /DraggableFlatList/);
  assert.match(panels, /onDragEnd=\{\(\{ data, from, to \}\) => \{ if \(from !== to\) void editing\.onReorder\(data\)/);
  assert.match(panels, /scrollEnabled=\{false\}/);
});

test("the legacy edit tab remains available as a temporary fallback", async () => {
  const panels = await source("src/components/panels/entity-panels.tsx");

  assert.match(panels, /const editTab =/);
  assert.match(panels, /FoodEditPanel/);
  assert.match(panels, /MealEditPanel/);
});
