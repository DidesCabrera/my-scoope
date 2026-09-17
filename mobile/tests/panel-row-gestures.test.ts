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
  assert.match(panels, /DirectionalSwipeSurface[\s\S]*?progress\.value > 0[\s\S]*?direction\.value ===/);
  assert.match(panels, /setSwipeSide\(direction === SwipeDirection\.RIGHT \? "left" : "right"\)/);
  assert.match(panels, /onSwipeableClose=\{\(\) => \{ swipeDirection\.value = 0; setSwipeSide\("neutral"\)/);
  assert.match(panels, /overshootLeft[\s\S]*?overshootRight/);
  assert.match(panels, /swipeOvershootLeft[\s\S]*?swipeSide === "left" && editing\.onChangeTime \? "#3A86FF" : tokens\.color\.surfaceMuted/);
  assert.match(panels, /swipeOvershootRight[\s\S]*?swipeSide === "right" \? "#515151" : tokens\.color\.surfaceMuted/);
  assert.match(panels, /containerStyle=\{styles\.swipeContainer\}/);

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
  assert.match(panels, /onDragBegin: \(\) => \{[\s\S]*?openSwipeableRef\.current\?\.close\(\)/);
});

test("owned library cards connect panel gestures to composition mutations", async () => {
  const card = await source("src/components/libraries/library-card.tsx");
  const list = await source("src/components/libraries/library-list-screen.tsx");
  const wrappers = await source("src/components/libraries/entity-panels.tsx");

  assert.match(card, /item\.entity === "meal" \? \{/);
  assert.match(card, /\/api\/v1\/library\/meals\/\$\{item\.id\}\/foods\/order/);
  assert.match(card, /item\.entity === "dailyPlan" \? \{/);
  assert.match(card, /\/api\/v1\/library\/daily-plans\/\$\{item\.id\}\/meals\/order/);
  assert.match(card, /onChangeTime: setTimeChangeMeal/);
  assert.match(card, /<CalendarizedEntityActions[\s\S]*?initialAction="change-time"/);
  assert.match(card, /method: "PATCH"/);
  assert.match(card, /<FoodPanels editing=\{foodEditing\}/);
  assert.match(card, /<MealPanels[^>]*editing=\{mealEditing\}/);
  assert.match(card, /items=\{item\.panel\.foods\} nestedScroll/);
  assert.match(card, /items=\{item\.panel\.meals\} nestedScroll/);
  assert.match(list, /<NestableScrollContainer/);
  assert.match(wrappers, /<SharedFoodPanels editing=\{editing\}/);
  assert.match(wrappers, /<SharedMealPanels editing=\{editing\}/);
});

test("in-progress plan cards connect meal gestures to their composition mutations", async () => {
  const today = await source("src/app/today.tsx");
  const planning = await source("src/components/calendarization/calendarized-program-planning.tsx");
  const calendarizedCard = await source("src/components/calendarization/calendarized-daily-plan-card.tsx");
  const pinnedCard = await source("src/components/calendarization/pinned-daily-plan-card.tsx");
  const layout = await source("src/components/ui/layout.tsx");

  assert.match(today, /calendarizedMealEditing: MealPanelEditing/);
  assert.match(today, /program\/days\/\$\{todayDayId\}\/meals\/order/);
  assert.match(today, /apiRequest<CalendarizedDayDetail>[\s\S]*?setToday\(\(current\)/);
  assert.match(today, /pinnedMealEditing: MealPanelEditing/);
  assert.match(today, /library\/daily-plans\/\$\{pinnedPlan\.id\}\/meals\/order/);
  assert.match(today, /const positions = new Map\(meals\.map/);
  assert.match(planning, /mealEditing: MealPanelEditing/);
  assert.match(planning, /program\/days\/\$\{detail\.id\}\/meals\/order/);
  assert.match(calendarizedCard, /<MealPanels[\s\S]*?editing=\{cardEditing\}/);
  assert.match(calendarizedCard, /<MealPanels[\s\S]*?nestedScroll/);
  assert.match(calendarizedCard, /<CalendarizedEntityActions[\s\S]*?initialAction="change-time"/);
  assert.match(pinnedCard, /<MealPanels[\s\S]*?editing=\{cardEditing\}/);
  assert.match(pinnedCard, /<MealPanels[\s\S]*?nestedScroll/);
  assert.match(pinnedCard, /<CalendarizedEntityActions[\s\S]*?initialAction="change-time"/);
  assert.match(layout, /<NestableScrollContainer/);
});

test("meal rows reveal a clock action on right swipe and reuse existing time forms", async () => {
  const panels = await source("src/components/panels/entity-panels.tsx");
  const calendarizedDay = await source("src/app/program/days/[id].tsx");
  const libraryDetail = await source("src/components/libraries/library-detail-screen.tsx");

  assert.match(panels, /renderLeftActions = editing\.onChangeTime/);
  assert.match(panels, /label="Cambiar hora"/);
  assert.match(panels, /<Clock color=\{tokens\.color\.entityIconForeground\}/);
  assert.match(panels, /swipeAction: \{[^}]*alignSelf: "stretch"[^}]*flex: 1/);
  assert.match(panels, /swipeAction: \{[^}]*backgroundColor: "#515151"/);
  assert.match(panels, /swipeActionTime: \{ backgroundColor: "#3A86FF" \}/);
  assert.match(panels, /swipeActionDestructive: \{ backgroundColor: "#DB294A" \}/);
  assert.match(panels, /preparationMarkerChecked: \{ backgroundColor: tokens\.color\.food/);
  assert.match(panels, /onChangeTime: editing\.onChangeTime/);
  assert.match(calendarizedDay, /onChangeTime: setTimeChangeMeal/);
  assert.match(calendarizedDay, /initialAction="change-time"[\s\S]*?method: "PATCH"/);
  assert.match(libraryDetail, /onChangeTime: \(meal: MealPanelItem\)/);
  assert.match(libraryDetail, /initialAction="change-time"[\s\S]*?method: "PATCH"/);
});

test("program day and week comparison tables expose measured swipe actions and drag reordering", async () => {
  const gestureRows = await source("src/components/libraries/comparison-panel-gesture-rows.tsx");
  const dependencyPatch = await source("patches/react-native-draggable-flatlist+4.0.3.patch");
  const dayPanels = await source("src/components/libraries/program-day-comparison-panels.tsx");
  const weekPanels = await source("src/components/libraries/program-week-comparison-panels.tsx");
  const programDetail = await source("src/components/libraries/program-detail-preview.tsx");
  const libraryDetail = await source("src/components/libraries/library-detail-screen.tsx");

  assert.match(gestureRows, /ReanimatedSwipeable/);
  assert.match(gestureRows, /width: actions\.length \* 48/);
  assert.match(gestureRows, /delayLongPress=\{320\}/);
  assert.match(gestureRows, /onLongPress=\{\(\) => beginComparisonPanelDrag\(drag\)\}/);
  assert.match(gestureRows, /Haptics\.impactAsync\(Haptics\.ImpactFeedbackStyle\.Rigid\)/);
  assert.match(gestureRows, /DirectionalSwipeSurface[\s\S]*?progress\.value > 0[\s\S]*?direction\.value ===/);
  assert.match(gestureRows, /overshootLeft[\s\S]*?overshootRight/);
  assert.match(gestureRows, /adjacentActionColor = actions\[0\]\?\.backgroundColor/);
  assert.match(gestureRows, /swipeOvershootRight[\s\S]*?swipeSide === "right" \? adjacentActionColor : tokens\.color\.surfaceMuted/);
  assert.match(gestureRows, /containerStyle=\{styles\.swipeContainer\}/);
  assert.doesNotMatch(gestureRows, /GestureDetector|Gesture\.LongPress/);
  assert.match(gestureRows, /borderTopWidth: 1/);
  assert.match(gestureRows, /shadowOpacity: 0\.14/);
  assert.match(gestureRows, /isActive \? <View pointerEvents="none" style=\{styles\.rowBottomBorder\}/);
  assert.match(gestureRows, /rowBottomBorder: \{ backgroundColor: tokens\.color\.borderDefault, bottom: 0, height: 1/);
  assert.match(gestureRows, /NestableDraggableFlatList/);
  assert.match(gestureRows, /activationDistance=\{20\}/);
  assert.match(gestureRows, /onDragEnd=\{\(\{ data, from, to \}\)/);
  assert.match(programDetail, /NestableScrollContainer/);
  assert.match(programDetail, /<ProgramWeekComparisonPanels onDelete=\{onRemoveWeek\} onDuplicate=\{onDuplicateWeek\} onReorder=\{onReorderWeeks\}/);
  assert.match(dependencyPatch, /panGesture\.failOffsetX\(activeOffset\)/);
  assert.match(dependencyPatch, /panGesture\.failOffsetY\(activeOffset\)/);
  assert.doesNotMatch(dependencyPatch, /panGesture\.simultaneousWithExternalGesture/);
  assert.match(dependencyPatch, /simultaneousHandlers=\{props\.simultaneousHandlers \?\? scrollableRef\}/);
  assert.match(dependencyPatch, /\.onFinalize\(\(_evt, success\) =>/);
  assert.match(dependencyPatch, /runOnJS\(onDragCancel\)\(activeIndexAnim\.value\)/);
  assert.match(dependencyPatch, /const onRelease:[\s\S]*?setOuterScrollEnabled\(true\)/);
  assert.match(dependencyPatch, /const onDragEnd = useStableCallback\([\s\S]*?onDragEnd\?\.\(\{ from, to, data: newData \}\);[\s\S]*?reset\(\);/);
  assert.match(dependencyPatch, /\.manualActivation\(true\)/);
  assert.match(dependencyPatch, /\.onTouchesMove\(\(evt, stateManager\) =>/);
  assert.match(dependencyPatch, /if \(activeIndexAnim\.value !== -1\) \{[\s\S]*?stateManager\.activate\(\)/);
  assert.match(dependencyPatch, /if \(movedX > 4 \|\| movedY > 4\) stateManager\.fail\(\)/);
  assert.match(dayPanels, /ComparisonPanelGestureRows/);
  assert.match(dayPanels, /Reemplazar.*Agregar/);
  assert.match(dayPanels, /backgroundColor: "#515151"/);
  assert.match(dayPanels, /backgroundColor: "#DB294A"/);
  assert.match(dayPanels, /Eliminar plan de/);
  assert.match(dayPanels, /sourceRows\.find\(\(\{ id \}\) => id === row\.id\)\?\.dayNumber/);
  assert.match(dayPanels, /await onReorder\(week, orderedDays\)/);
  assert.match(dayPanels, /onLongPress=\{\(\) => beginComparisonPanelDrag\(drag\)\}/);
  assert.match(dayPanels, /editRowActive: \{[\s\S]*?borderTopWidth: 1[\s\S]*?shadowOpacity: 0\.14/);
  assert.match(dayPanels, /backgroundColor: "#3a3a3a"/);
  assert.match(weekPanels, /ComparisonPanelGestureRows/);
  assert.match(weekPanels, /Duplicar Semana/);
  assert.match(weekPanels, /backgroundColor: "#515151"/);
  assert.match(weekPanels, /backgroundColor: "#DB294A"/);
  assert.match(weekPanels, /Eliminar Semana/);
  assert.match(weekPanels, /weeks\.find\(\(\{ id \}\) => id === week\.id\)\?\.week/);
  assert.match(weekPanels, /await onReorder\(sourceWeekNumbers\)/);
  assert.match(weekPanels, /onLongPress=\{\(\) => beginComparisonPanelDrag\(drag\)\}/);
  assert.match(weekPanels, /editRowActive: \{[\s\S]*?borderTopWidth: 1[\s\S]*?shadowOpacity: 0\.14/);
  assert.match(weekPanels, /backgroundColor: "#3a3a3a"/);
  assert.match(programDetail, /onReorderDailyPlans/);
  assert.match(libraryDetail, /weeks\/\$\{week\}\/days\/order/);
});

test("editable rows reorder after a deliberate long press and persist on drop", async () => {
  const panels = await source("src/components/panels/entity-panels.tsx");
  const calendarizedDay = await source("src/app/program/days/[id].tsx");
  const calendarizedMeal = await source("src/app/program/days/[id]/meals/[mealKey].tsx");
  const libraryDetail = await source("src/components/libraries/library-detail-screen.tsx");
  const layout = await source("src/app/_layout.tsx");

  assert.match(layout, /GestureHandlerRootView style=\{styles\.gestureRoot\}/);
  assert.match(panels, /delayLongPress=\{320\}/);
  assert.match(panels, /const onLongPress = \(\) => beginDrag\(drag, \(\) =>/);
  assert.match(panels, /row=\{renderRow\(item, getIndex\(\) \?\? 0, dragInteraction\)\}/);
  assert.match(panels, /<Pressable \{\.\.\.dragInteraction\} accessibilityLabel=\{`Ver detalle de/);
  assert.match(panels, /onLongPress=\{dragInteraction\?\.onLongPress\}/);
  assert.match(panels, /Haptics\.impactAsync\(Haptics\.ImpactFeedbackStyle\.Rigid\)/);
  assert.match(panels, /if \(!nestedScroll\) setPanelDragging\(true\)/);
  assert.match(panels, /NestableDraggableFlatList/);
  assert.match(panels, /DraggableFlatList/);
  assert.match(panels, /activationDistance: 20/);
  assert.match(panels, /onDragEnd: \(\{ data, from, to \}/);
  assert.match(panels, /void editing\.onReorder\(data\)/);
  assert.match(panels, /scrollEnabled: false/);
  assert.match(panels, /nestedScroll \? <NestableDraggableFlatList/);
  assert.match(panels.match(/function FoodEditPanel[\s\S]*?function MealEditPanel/)?.[0] ?? "", /<NestableDraggableFlatList/);
  assert.match(panels.match(/function MealEditPanel[\s\S]*?export function FoodPanels/)?.[0] ?? "", /<NestableDraggableFlatList/);
  assert.match(libraryDetail, /NestableScrollContainer/);
  assert.match(calendarizedDay, /NestableScrollContainer/);
  assert.match(calendarizedMeal, /NestableScrollContainer/);
});

test("cards hide the edit tab while entity details keep it available", async () => {
  const panels = await source("src/components/panels/entity-panels.tsx");
  const dayPanels = await source("src/components/libraries/program-day-comparison-panels.tsx");
  const weekPanels = await source("src/components/libraries/program-week-comparison-panels.tsx");
  const libraryCard = await source("src/components/libraries/library-card.tsx");
  const libraryDetail = await source("src/components/libraries/library-detail-screen.tsx");
  const calendarizedCard = await source("src/components/calendarization/calendarized-daily-plan-card.tsx");
  const pinnedCard = await source("src/components/calendarization/pinned-daily-plan-card.tsx");
  const calendarizedMealDetail = await source("src/app/program/days/[id]/meals/[mealKey].tsx");

  assert.match(panels, /const editTab =/);
  assert.match(panels, /showEditTab = true/);
  assert.match(panels, /editing && showEditTab \? \[\.\.\.foodTabs, editTab\] : foodTabs/);
  assert.match(panels, /editing && showEditTab \? \[\.\.\.mealTabs, editTab\] : mealTabs/);
  assert.match(libraryCard, /<FoodPanels[^>]*showEditTab=\{false\}/);
  assert.match(libraryCard, /<MealPanels[^>]*showEditTab=\{false\}/);
  assert.match(calendarizedCard, /<MealPanels[\s\S]*?showEditTab=\{false\}/);
  assert.match(pinnedCard, /<MealPanels[\s\S]*?showEditTab=\{false\}/);
  assert.match(libraryDetail, /<FoodPanels editing=\{foodEditing\}/);
  assert.match(libraryDetail, /<MealPanels editing=\{mealEditing\}/);
  assert.match(calendarizedMealDetail, /<FoodPanels[\s\S]*?editing=\{/);
  assert.match(dayPanels, /key: "edit", label: "Editar días"/);
  assert.match(weekPanels, /key: "edit", label: "Editar"/);
  assert.match(panels, /FoodEditPanel/);
  assert.match(panels, /MealEditPanel/);
  for (const sourceCode of [panels, dayPanels, weekPanels]) {
    assert.match(sourceCode, /GripVertical/);
    assert.match(sourceCode, /(?:const onLongPress = \(\) => beginDrag\(drag, \(\) =>|onLongPress=\{\(\) => beginComparisonPanelDrag\(drag\)\})/);
    assert.match(sourceCode, /onDragEnd=/);
    assert.doesNotMatch(sourceCode, /ArrowUp|ArrowDown|label=\{`Subir|label=\{`Bajar/);
  }
  assert.match(panels, /label=\{`Cambiar hora de \$\{item\.name\}`\}[\s\S]*?<Clock/);
  assert.match(panels, />Porción<\/Text>/);
  assert.match(panels, /decimal\(item\.quantity\)[\s\S]*?item\.quantityUnit/);
  assert.match(panels, />Hora<\/Text>/);
  assert.match(panels, /styles\.editValue, styles\.editTimeValue\]\}>\{item\.time \?\? "—"\}/);
  assert.match(panels, /editDragHandle: \{[^}]*width: 20/);
  assert.match(panels, /editPortionValue: \{ color: tokens\.color\.textMain \}/);
  assert.match(panels, /editTimeValue: \{ color: tokens\.color\.textMain \}/);
  assert.match(panels, /<GripVertical color=\{tokens\.color\.textMuted\}/);
  assert.match(panels, /<Trash2 color=\{tokens\.color\.danger\}/);
  assert.doesNotMatch(panels, /Guardar orden|Descartar/);
  assert.match(panels, /borderTopWidth: 1/);
  assert.match(panels, /shadowOpacity: 0\.14/);
  assert.match(panels, /backgroundColor: "#3a3a3a"/);
  assert.match(panels, /isActive \? <View pointerEvents="none" style=\{styles\.gestureRowBottomBorder\}/);
  assert.match(panels, /gestureRowBottomBorder: \{ backgroundColor: tokens\.color\.borderDefault, bottom: 0, height: 1/);
  assert.doesNotMatch(panels, /menuRowPressed/);
  assert.doesNotMatch(weekPanels, /Guardar orden|Descartar/);
  assert.match(panels, /onDragEnd=\{\(\{ data, from, to \}\) => \{[\s\S]*?editing\.onReorder\(data\)/);
  assert.match(weekPanels, /onDragEnd=\{\(\{ data, from, to \}\) => \{[\s\S]*?onReorder\(data\.map/);
  assert.match(dayPanels, /onReorder=\{gestures\.onReorder\}/);
});
