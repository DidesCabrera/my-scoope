import { type Href, useRouter } from "expo-router";
import { BookmarkCheck, BookmarkPlus, ChevronRight } from "lucide-react-native";
import { useState } from "react";
import { StyleSheet, View } from "react-native";
import type { LibraryActionResult, LibraryItem } from "@/api/types";
import { NutritionEntityCard } from "@/components/nutrition";
import { FoodNutritionPanel, FoodPanels as SharedFoodPanels, type FoodPanelEditing, type FoodPanelItem, type MealPanelEditing, type MealPanelItem } from "@/components/panels";
import { pickerConfigureHref, pickerHref } from "@/components/pickers/composition-picker-screen";
import { Button, EntityCardAction, MutationStatusModal, useMutationStatus } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { CalendarizedEntityActions } from "@/components/calendarization/calendarized-entity-actions";
import { useComparatorSelectionTransfer } from "@/components/comparisons/comparator-selection-context";
import { SupplementIntakePanel } from "@/components/supplements/supplement-intake-panel";
import { SupplementProSheet } from "@/components/supplements/supplement-pro-sheet";

import { FoodPanels, MealPanels, ProgramPanels, mealFoodPanelItems } from "./entity-panels";
import { libraryFoodNutritionFacts, libraryNutrition } from "./presentation-adapters";
import { ProgramChildCard, programDailyMetricData } from "./program-child-card";
import { LibraryActions } from "./library-actions";
import { MealComponentAddActions } from "./meal-component-add-actions";

function indicatorValue(item: LibraryItem, icon: "week" | "dailyPlan" | "food"): number {
  const value = item.indicators.find((indicator) => indicator.icon === icon)?.value;
  return typeof value === "number" ? value : Number.parseInt(String(value ?? 0), 10) || 0;
}

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export function LibraryCard({ apiRequest, detailHref: detailHrefOverride, interactive = true, item, navigable = interactive, onChanged, onSaveToLibrary, savedToLibrary = false, savingToLibrary = false }: { apiRequest: ApiRequest; detailHref?: Href; interactive?: boolean; item: LibraryItem; navigable?: boolean; onChanged(result: LibraryActionResult): Promise<void> | void; onSaveToLibrary?: () => Promise<void> | void; savedToLibrary?: boolean; savingToLibrary?: boolean }) {
  const router = useRouter();
  const { publishSelection } = useComparatorSelectionTransfer();
  const [timeChangeMeal, setTimeChangeMeal] = useState<MealPanelItem | null>(null);
  const [supplementUpsell, setSupplementUpsell] = useState(false);
  const [addComponentVisible, setAddComponentVisible] = useState(false);
  const { clearStatus, runWithStatus, status: mutationStatus } = useMutationStatus();
  const segment = item.entity === "dailyPlan" ? "daily-plans" : item.entity === "program" ? "programs" : item.entity === "meal" ? "meals" : "foods";
  const detailHref = detailHrefOverride ?? `/libraries/${segment}/${item.id}` as Href;
  const libraryHref = `/libraries/${segment}` as Href;
  const mealComponents = item.entity === "meal" && item.panel.kind === "foods" ? mealFoodPanelItems(item.panel, item.nutrition) : [];
  const openDetail = () => router.push(detailHref);
  const openMealComponent = (component: FoodPanelItem) => {
    if (component.detailId == null) return;
    if (component.kind === "preparation") {
      const preparation = item.panel.preparations?.find((row) => row.relation_id === component.relationId);
      if (!preparation) return;
      router.push({ pathname: "/libraries/preparations/[id]", params: {
        id: String(component.detailId), mealId: String(item.id), relationId: String(preparation.relation_id),
        ...(preparation.selection_mode === "units" ? { units: String(preparation.selected_units ?? 1) } : { grams: String(preparation.quantity_g) }),
      } } as Href);
      return;
    }
    router.push(`/libraries/foods/${component.detailId}` as Href);
  };
  const addFood = () => router.push(pickerHref("food-to-meal", { mealId: item.id, returnTo: String(libraryHref) }));
  const addPreparation = () => router.push(`/pickers/preparation-to-meal?mealId=${item.id}` as Href);
  const canCalendarize = item.entity === "dailyPlan" && !item.is_draft;
  const openCalendarAssignment = () => router.push({ pathname: "/calendar/select-plans", params: { dailyPlanId: String(item.id), origin: "library", returnTo: String(libraryHref) } });
  const openEdit = () => router.push({ pathname: "/libraries/create", params: { entity: "food", id: String(item.id) } });
  const openComparison = () => {
    if (item.entity !== "meal" && item.entity !== "dailyPlan") return;
    const comparisonKind = item.entity === "meal" ? "meals" : "dailyplans";
    publishSelection({
      kind: comparisonKind,
      option: {
        entity: item.entity,
        id: item.id,
        indicators: item.indicators,
        name: item.name,
        nutrition: item.nutrition,
        panel: item.panel,
        quantity_unit: item.quantity_unit,
        subtitle: item.subtitle,
      },
      slotKey: 1,
    });
    router.push({ pathname: "/comparator", params: { create: "1", kind: comparisonKind } } as Href);
  };
  const refresh = (message: string) => onChanged({ action: "rename", item_id: item.id, message });
  const mutate = async (path: string, init: RequestInit, message: string, feedback?: { loadingLabel: string; successLabel: string }) => {
    const action = async () => {
      await apiRequest(path, init);
      await refresh(message);
    };
    if (feedback) await runWithStatus(action, feedback);
    else await action();
  };
  const foodEditing: FoodPanelEditing | undefined = interactive && item.entity === "meal" ? {
    onDelete: async (food) => { if (food.relationId != null) await mutate(`/api/v1/library/meals/${item.id}/foods/${food.relationId}`, { method: "DELETE" }, "Alimento eliminado"); },
    onEditPortion: (food) => { if (food.detailId != null && food.relationId != null) router.push(pickerConfigureHref("food-to-meal", { relationId: food.relationId, selectedId: food.detailId, targetId: item.id, weekNumber: 1 })); },
    onReorder: async (foods: FoodPanelItem[]) => mutate(`/api/v1/library/meals/${item.id}/foods/order`, { body: JSON.stringify({ ordered_ids: foods.map((food) => food.relationId) }), method: "PUT" }, "Orden actualizado", { loadingLabel: "Actualizando comida", successLabel: "Comida actualizada" }),
    onReplace: (food) => { if (food.relationId != null) router.push(pickerHref("food-to-meal", { mealFoodId: food.relationId, mealId: item.id })); },
  } : undefined;
  const openMeal = (meal: MealPanelItem) => {
    if (meal.detailId == null || meal.relationId == null) return;
    router.push({ pathname: "/libraries/meals/[id]", params: { dailyPlanId: String(item.id), dailyPlanMealId: String(meal.relationId), id: String(meal.detailId), mealTime: meal.time ?? "" } } as Href);
  };
  const mealEditing: MealPanelEditing | undefined = interactive && item.entity === "dailyPlan" ? {
    onChangeTime: setTimeChangeMeal,
    onDelete: async (meal) => { if (meal.relationId != null) await mutate(`/api/v1/library/daily-plans/${item.id}/meals/${meal.relationId}`, { method: "DELETE" }, "Comida eliminada"); },
    onOpen: openMeal,
    onReorder: async (meals: MealPanelItem[]) => mutate(`/api/v1/library/daily-plans/${item.id}/meals/order`, { body: JSON.stringify({ ordered_ids: meals.map((meal) => meal.relationId) }), method: "PUT" }, "Orden actualizado", { loadingLabel: "Actualizando minuta", successLabel: "Minuta actualizada" }),
    onReplace: (meal) => { if (meal.relationId != null) router.push(pickerHref("meal-to-dailyplan", { dailyPlanId: item.id, dailyPlanMealId: meal.relationId })); },
  } : undefined;
  if (item.entity === "program") {
    const metrics = item.panel.kind === "weeks" ? programDailyMetricData(item.panel.weeks) : [];
    const card = (onMore?: () => void) => (
      <ProgramChildCard
        axisLabels={item.panel.kind === "weeks" ? item.panel.weeks.map((week) => `S${week.week_number}`) : []}
        filledDaysCount={indicatorValue(item, "dailyPlan")}
        foodsCount={indicatorValue(item, "food")}
        metricData={metrics}
        onMore={onMore}
        onOpen={navigable ? openDetail : undefined}
        headingLink={navigable ? { label: `Ver detalle de ${item.name}`, onPress: openDetail } : undefined}
        title={item.name}
        weeksCount={indicatorValue(item, "week")}
      />
    );
    if (!interactive) return card();
    return item.actions?.length ? (
      <LibraryActions apiRequest={apiRequest} entitySlug={segment} item={item} onCompleted={onChanged} renderTrigger={(open) => card(open)} />
    ) : card();
  }
  return (<>
    <NutritionEntityCard actions={interactive || navigable || onSaveToLibrary ? <>{interactive && (item.actions?.length || canCalendarize) ? <LibraryActions apiRequest={apiRequest} entitySlug={segment} item={item} onCalendarize={canCalendarize ? openCalendarAssignment : undefined} onCompare={item.entity === "meal" || item.entity === "dailyPlan" ? openComparison : undefined} onCompleted={onChanged} onEdit={item.entity === "food" ? openEdit : undefined} /> : null}{onSaveToLibrary ? <EntityCardAction label={savedToLibrary ? `${item.name} guardada en tu biblioteca` : `Guardar ${item.name} en mi biblioteca`} onPress={() => { if (!savedToLibrary && !savingToLibrary) void onSaveToLibrary(); }}>{savedToLibrary ? <BookmarkCheck color={tokens.color.success} size={22} strokeWidth={2.2} /> : <BookmarkPlus color={savingToLibrary ? tokens.color.textSoft : tokens.color.textMain} size={22} strokeWidth={2.2} />}</EntityCardAction> : null}{navigable ? <EntityCardAction label={`Ver detalle de ${item.name}`} onPress={openDetail} role="link"><ChevronRight color={tokens.color.textMuted} size={19} strokeWidth={2.2} /></EntityCardAction> : null}</> : undefined} collapsiblePanel dailyPlanFoodsPanel={item.entity === "dailyPlan" ? <FoodPanels items={item.panel.foods} nestedScroll showEditTab={false} /> : undefined} entity={item.entity} foodEmoji={item.emoji} foodVisualKey={item.visual_key} headingLink={navigable ? { label: `Ver detalle de ${item.name}`, onPress: openDetail } : undefined} indicators={item.indicators} nutrition={libraryNutrition(item.nutrition)} onLockedSupplementPress={item.entity === "dailyPlan" && item.supplements_available && item.can_use_supplements === false ? () => setSupplementUpsell(true) : undefined} supplementPanel={item.entity === "dailyPlan" && item.can_use_supplements ? <SupplementIntakePanel dailyPlanId={item.id} editable={interactive} intakes={item.panel.supplement_intakes ?? []} /> : undefined} subtitle={item.subtitle || undefined} title={item.name}>
      {item.entity === "food" ? <FoodNutritionPanel facts={libraryFoodNutritionFacts(item.nutrition, item.food_nutrition)} portion={{ quantity: item.default_portion ?? null, unit: item.quantity_unit ?? "g" }} /> : null}
      {item.panel.kind === "foods" ? item.entity === "meal" ? <SharedFoodPanels editing={foodEditing} items={mealComponents} nestedScroll onOpenItem={openMealComponent} showEditTab={false} /> : <FoodPanels editing={foodEditing} items={item.panel.foods} nestedScroll showEditTab={false} /> : null}
      {item.panel.kind === "meals" ? <MealPanels dailyPlanId={item.entity === "dailyPlan" ? item.id : undefined} editing={mealEditing} items={item.panel.meals} nestedScroll showEditTab={false} /> : null}
      {item.panel.kind === "weeks" ? <ProgramPanels items={item.panel.weeks} /> : null}
      {interactive && item.entity === "meal" ? <View style={styles.addAction}><Button label="+ Agregar alimento o preparación" onPress={() => setAddComponentVisible(true)} variant="chipPrimary" /></View> : null}
      {interactive && item.entity === "dailyPlan" ? <View style={styles.addAction}><Button label="+ Agregar Comida" onPress={() => router.push(pickerHref("meal-to-dailyplan", { dailyPlanId: item.id, returnTo: String(libraryHref) }))} variant="chipPrimary" /></View> : null}
    </NutritionEntityCard>
    <CalendarizedEntityActions entityName={timeChangeMeal?.name ?? "Comida"} initialAction="change-time" key={timeChangeMeal?.id ?? "closed-library-card-time-change"} onVisibleChange={(visible) => { if (!visible) setTimeChangeMeal(null); }} timeChange={timeChangeMeal?.relationId != null ? { initialTime: timeChangeMeal.time, onSubmit: async (hour) => mutate(`/api/v1/library/daily-plans/${item.id}/meals/${timeChangeMeal.relationId}`, { body: JSON.stringify({ hour }), headers: { "Content-Type": "application/json" }, method: "PATCH" }, "Hora actualizada") } : undefined} visible={timeChangeMeal != null} />
    <MutationStatusModal onFinished={clearStatus} status={mutationStatus} />
    <MealComponentAddActions onClose={() => setAddComponentVisible(false)} onFood={addFood} onPreparation={addPreparation} visible={addComponentVisible && interactive && item.entity === "meal"} />
    <SupplementProSheet onClose={() => setSupplementUpsell(false)} visible={supplementUpsell} />
  </>);
}

const styles = StyleSheet.create({
  addAction: { marginTop: tokens.spacing.md },
});
