import type { LibraryFoodPanelItem, LibraryMealPanelItem, PickerPreview } from "@/api/types";
import { ProgramDayComparisonPanels, type ProgramDayNutrition } from "@/components/libraries/program-day-comparison-panels";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { NutritionEntityCard } from "@/components/nutrition";
import { FoodPanels, MealPanels, type FoodPanelItem, type MealPanelItem } from "@/components/panels";
import { EntityCard, EntityCardPanelSlot } from "@/components/ui";

function foodPanelItem(item: LibraryFoodPanelItem): FoodPanelItem {
  return {
    id: item.id,
    relationId: item.relation_id,
    name: item.name,
    quantity: item.quantity,
    quantityUnit: item.quantity_unit,
    calories: item.calories,
    calorieShare: item.calorie_share,
    proteinGrams: item.protein_grams,
    carbsGrams: item.carbs_grams,
    fatGrams: item.fat_grams,
    proteinAllocation: item.protein_allocation,
    carbsAllocation: item.carbs_allocation,
    fatAllocation: item.fat_allocation,
    projectedLabel: item.projected_label,
  };
}

function mealPanelItem(item: LibraryMealPanelItem): MealPanelItem {
  return {
    id: item.id,
    relationId: item.relation_id,
    detailId: item.detail_id,
    name: item.name,
    time: item.time?.slice(0, 5),
    note: item.note,
    foods: item.foods.map((food) => ({ name: food.name, quantity: food.quantity, quantityUnit: food.quantity_unit })),
    calories: item.calories,
    calorieShare: item.calorie_share,
    proteinGrams: item.protein_grams,
    carbsGrams: item.carbs_grams,
    fatGrams: item.fat_grams,
    proteinAllocation: item.protein_allocation,
    carbsAllocation: item.carbs_allocation,
    fatAllocation: item.fat_allocation,
    projectedLabel: item.projected_label,
  };
}

function weekRows(preview: PickerPreview): ProgramDayNutrition[] {
  const week = preview.result?.panel.weeks[0];
  if (!week) return [];
  return week.days.map((day) => ({
    allocation: {
      protein: day.nutrition?.protein.allocation ?? 0,
      carbs: day.nutrition?.carbs.allocation ?? 0,
      fat: day.nutrition?.fat.allocation ?? 0,
    },
    calorieShare: day.nutrition ? day.nutrition.calories / Math.max(week.calories, 1) * 100 : 0,
    calories: day.nutrition?.calories ?? 0,
    carbsGrams: day.nutrition?.carbs.grams ?? 0,
    day: day.day_label,
    dayNumber: day.day_number ?? 1,
    fatGrams: day.nutrition?.fat.grams ?? 0,
    id: day.id ?? `${week.id}:${day.day_number ?? day.day_label}`,
    planName: day.plan_name,
    ppk: day.nutrition?.protein.per_kilogram ?? 0,
    projectedLabel: day.projected_label,
    proteinGrams: day.nutrition?.protein.grams ?? 0,
    week: week.week_number,
  }));
}

export function PickerResultCard({ preview }: { preview: PickerPreview }) {
  const result = preview.result;
  if (!result) return null;
  const week = result.panel.weeks[0];
  const entity = result.entity === "week" ? "program" : result.entity;
  const projectedMeal = preview.selection.entity === "food" && result.panel.kind === "meals"
    ? result.panel.meals.find((meal) => meal.is_projected)
    : undefined;
  if (result.entity === "week" && week) {
    return (
      <EntityCard entity="program" eyebrow="Resultado proyectado" title={result.name}>
        <EntityCardPanelSlot>
          <ProgramDayComparisonPanels rows={weekRows(preview)} week={week.week_number} />
        </EntityCardPanelSlot>
      </EntityCard>
    );
  }
  return (
    <>
      {projectedMeal ? (
        <NutritionEntityCard
          entity="meal"
          eyebrow="Comida resultante"
          indicators={[{ icon: "food", label: "alimentos", value: projectedMeal.foods.length }]}
          nutrition={libraryNutrition({
            calories: projectedMeal.calories,
            protein: { grams: projectedMeal.protein_grams, allocation: projectedMeal.protein_allocation, per_kilogram: projectedMeal.protein_per_kilogram },
            carbs: { grams: projectedMeal.carbs_grams, allocation: projectedMeal.carbs_allocation },
            fat: { grams: projectedMeal.fat_grams, allocation: projectedMeal.fat_allocation },
          })}
          title={projectedMeal.name}>
          <FoodPanels items={projectedMeal.foods.map(foodPanelItem)} />
        </NutritionEntityCard>
      ) : null}
      <NutritionEntityCard
        entity={entity}
        eyebrow={result.entity === "meal" ? "Comida resultante" : result.entity === "dailyPlan" ? "Plan diario resultante" : "Resultado proyectado"}
        indicators={result.indicators}
        nutrition={libraryNutrition(result.nutrition)}
        title={result.name}>
        {result.panel.kind === "foods" ? <FoodPanels items={result.panel.foods.map(foodPanelItem)} /> : null}
        {result.panel.kind === "meals" ? <MealPanels items={result.panel.meals.map(mealPanelItem)} /> : null}
      </NutritionEntityCard>
    </>
  );
}
