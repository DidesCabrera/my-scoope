import { type Href, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useState } from "react";
import type { LibraryActionResult, LibraryItem } from "@/api/types";
import { NutritionEntityCard } from "@/components/nutrition";
import type { FoodPanelEditing, FoodPanelItem, MealPanelEditing, MealPanelItem } from "@/components/panels";
import { pickerConfigureHref, pickerHref } from "@/components/pickers/composition-picker-screen";
import { EntityCardAction } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { CalendarizedEntityActions } from "@/components/calendarization/calendarized-entity-actions";

import { FoodPanels, MealPanels, ProgramPanels } from "./entity-panels";
import { libraryNutrition } from "./presentation-adapters";
import { ProgramChildCard, programDailyMetricData } from "./program-child-card";
import { LibraryActions } from "./library-actions";

function indicatorValue(item: LibraryItem, icon: "week" | "dailyPlan" | "food"): number {
  const value = item.indicators.find((indicator) => indicator.icon === icon)?.value;
  return typeof value === "number" ? value : Number.parseInt(String(value ?? 0), 10) || 0;
}

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export function LibraryCard({ apiRequest, interactive = true, item, onChanged }: { apiRequest: ApiRequest; interactive?: boolean; item: LibraryItem; onChanged(result: LibraryActionResult): void }) {
  const router = useRouter();
  const [timeChangeMeal, setTimeChangeMeal] = useState<MealPanelItem | null>(null);
  const segment = item.entity === "dailyPlan" ? "daily-plans" : item.entity === "program" ? "programs" : item.entity === "meal" ? "meals" : "foods";
  const detailHref = `/libraries/${segment}/${item.id}` as Href;
  const refresh = (message: string) => onChanged({ action: "rename", item_id: item.id, message });
  const mutate = async (path: string, init: RequestInit, message: string) => {
    await apiRequest(path, init);
    refresh(message);
  };
  const foodEditing: FoodPanelEditing | undefined = interactive && item.entity === "meal" ? {
    onDelete: async (food) => { if (food.relationId != null) await mutate(`/api/v1/library/meals/${item.id}/foods/${food.relationId}`, { method: "DELETE" }, "Alimento eliminado"); },
    onEditPortion: (food) => { if (food.detailId != null && food.relationId != null) router.push(pickerConfigureHref("food-to-meal", { relationId: food.relationId, selectedId: food.detailId, targetId: item.id, weekNumber: 1 })); },
    onReorder: async (foods: FoodPanelItem[]) => mutate(`/api/v1/library/meals/${item.id}/foods/order`, { body: JSON.stringify({ ordered_ids: foods.map((food) => food.relationId) }), method: "PUT" }, "Orden actualizado"),
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
    onReorder: async (meals: MealPanelItem[]) => mutate(`/api/v1/library/daily-plans/${item.id}/meals/order`, { body: JSON.stringify({ ordered_ids: meals.map((meal) => meal.relationId) }), method: "PUT" }, "Orden actualizado"),
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
        onOpen={interactive ? () => router.push(detailHref) : undefined}
        owner={item.creator}
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
    <NutritionEntityCard actions={interactive ? <>{item.actions?.length ? <LibraryActions apiRequest={apiRequest} entitySlug={segment} item={item} onCompleted={onChanged} /> : null}<EntityCardAction label={`Ver detalle de ${item.name}`} onPress={() => router.push(detailHref)} role="link"><ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} /></EntityCardAction></> : undefined} entity={item.entity} indicators={item.indicators} nutrition={libraryNutrition(item.nutrition)} subtitle={item.subtitle || undefined} title={item.name}>
      {item.panel.kind === "foods" ? <FoodPanels editing={foodEditing} items={item.panel.foods} nestedScroll showEditTab={false} /> : null}
      {item.panel.kind === "meals" ? <MealPanels dailyPlanId={item.entity === "dailyPlan" ? item.id : undefined} editing={mealEditing} items={item.panel.meals} nestedScroll showEditTab={false} /> : null}
      {item.panel.kind === "weeks" ? <ProgramPanels items={item.panel.weeks} /> : null}
    </NutritionEntityCard>
    <CalendarizedEntityActions entityName={timeChangeMeal?.name ?? "Comida"} initialAction="change-time" key={timeChangeMeal?.id ?? "closed-library-card-time-change"} onVisibleChange={(visible) => { if (!visible) setTimeChangeMeal(null); }} timeChange={timeChangeMeal?.relationId != null ? { initialTime: timeChangeMeal.time, onSubmit: async (hour) => mutate(`/api/v1/library/daily-plans/${item.id}/meals/${timeChangeMeal.relationId}`, { body: JSON.stringify({ hour }), headers: { "Content-Type": "application/json" }, method: "PATCH" }, "Hora actualizada") } : undefined} visible={timeChangeMeal != null} />
  </>);
}
