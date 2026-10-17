import type { LibraryFoodPanelItem, LibraryMealPanelItem, PickerPreview } from "@/api/types";
import { useState } from "react";
import { CalendarRange } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { programDailyMetricData, WeekMetricPreview, type WeekMetricFilter } from "@/components/libraries/program-child-card";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { NutritionEntityCard } from "@/components/nutrition";
import { EntityPanelTabs, FoodPanels, MealPanels, PanelSurface, type FoodPanelItem, type MealPanelItem } from "@/components/panels";
import { Card, EntityHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";

const weekMetricTabs: { key: WeekMetricFilter; label: string }[] = [
  { key: "calories", label: "Calorías" },
  { key: "ppk", label: "PPK" },
  { key: "macros", label: "Macros" },
  { key: "allocation", label: "Alloc" },
  { key: "all", label: "Todos" },
];

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
    proteinPerKilogram: item.protein_per_kilogram,
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
    proteinPerKilogram: item.protein_per_kilogram,
    carbsGrams: item.carbs_grams,
    fatGrams: item.fat_grams,
    proteinAllocation: item.protein_allocation,
    carbsAllocation: item.carbs_allocation,
    fatAllocation: item.fat_allocation,
    projectedLabel: item.projected_label,
  };
}

export function PickerResultCard({ preview }: { preview: PickerPreview }) {
  const [activeMetricTab, setActiveMetricTab] = useState<WeekMetricFilter>("calories");
  const result = preview.result;
  if (!result) return null;
  const week = result.panel.weeks[0];
  const entity = result.entity === "week" ? "program" : result.entity;
  const projectedMeal = preview.selection.entity === "food" && result.panel.kind === "meals"
    ? result.panel.meals.find((meal) => meal.is_projected)
    : undefined;
  if (result.entity === "week" && week) {
    return (
      <Card accent={tokens.color.program} style={styles.weekResult}>
        <View accessibilityLabel={`Previsualización Semana ${week.week_number}`}>
          <EntityHeading
            entity="program"
            eyebrow="Previsualización semana"
            identityIcon={CalendarRange}
            title={`Semana ${week.week_number}`}
          />
        </View>
        <View style={styles.weekChartGroup}>
          <View style={styles.weekTabsBleed}>
            <EntityPanelTabs activeTab={activeMetricTab} onChange={setActiveMetricTab} tabs={weekMetricTabs} />
          </View>
          <PanelSurface style={styles.weekChartPanel}>
            <View style={styles.weekChartPanelBody}>
              <WeekMetricPreview
                axisLabels={week.days.map((day) => day.day_label.slice(0, 1).toUpperCase())}
                data={programDailyMetricData([week])}
                days={7}
                filter={activeMetricTab}
              />
            </View>
          </PanelSurface>
        </View>
      </Card>
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

const styles = StyleSheet.create({
  weekResult: { gap: tokens.spacing.lg, minWidth: 0 },
  weekChartGroup: { gap: 0 },
  weekTabsBleed: { marginHorizontal: -(6 + tokens.spacing.sm) },
  weekChartPanel: { backgroundColor: tokens.color.surfaceCard, marginHorizontal: -tokens.card.outerPadding },
  weekChartPanelBody: { paddingBottom: tokens.spacing.lg, paddingHorizontal: tokens.layout.reducedInset, paddingTop: tokens.spacing.sm },
});
