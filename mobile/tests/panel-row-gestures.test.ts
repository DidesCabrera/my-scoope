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
  assert.doesNotMatch(panels.match(/function SwipeAction[\s\S]*?function confirmRowDeletion/)?.[0] ?? "", /<Text/);
  assert.match(panels, /swipeActions: \{[^}]*width: 144/);
  assert.match(panels, /swipeAction: \{[^}]*width: 48/);
  assert.match(panels, /accessibilityHint="Desliza hacia la izquierda para ver acciones/);

  for (const tab of ["quantity", "calories", "macros", "distribution", "allocation"]) {
    assert.match(panels, new RegExp(`activeTab === "${tab}"[\\s\\S]*?editing=\\{rowEditing\\}`));
  }
  for (const tab of ["menu", "calories", "macros", "distribution", "allocation"]) {
    assert.match(panels, new RegExp(`activeTab === "${tab}"[\\s\\S]*?editing=\\{rowEditing\\}`));
  }
});

test("opening one row closes the previously open swipe actions", async () => {
  const panels = await source("src/components/panels/entity-panels.tsx");

  assert.match(panels, /openSwipeableRef = useRef<SwipeableMethods \| null>/);
  assert.match(panels, /openSwipeableRef\.current !== methods\) openSwipeableRef\.current\.close\(\)/);
  assert.match(panels, /onSwipeableWillOpen=\{\(\) =>/);
  assert.match(panels, /onDragBegin=\{\(\) => \{[\s\S]*?openSwipeableRef\.current\?\.close\(\)/);
});

test("meal rows reveal a clock action on right swipe and reuse existing time forms", async () => {
  const panels = await source("src/components/panels/entity-panels.tsx");
  const calendarizedDay = await source("src/app/program/days/[id].tsx");
  const libraryDetail = await source("src/components/libraries/library-detail-screen.tsx");

  assert.match(panels, /renderLeftActions = editing\.onChangeTime/);
  assert.match(panels, /label="Cambiar hora"/);
  assert.match(panels, /<Clock color=\{tokens\.color\.entityIconForeground\}/);
  assert.match(panels, /onChangeTime: editing\.onChangeTime/);
  assert.match(calendarizedDay, /onChangeTime: setTimeChangeMeal/);
  assert.match(calendarizedDay, /initialAction="change-time"[\s\S]*?method: "PATCH"/);
  assert.match(libraryDetail, /onChangeTime: \(meal: MealPanelItem\)/);
  assert.match(libraryDetail, /initialAction="change-time"[\s\S]*?method: "PATCH"/);
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
