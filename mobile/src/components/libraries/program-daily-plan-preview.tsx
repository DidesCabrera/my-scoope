import { type Href, useRouter } from "expo-router";
import { ChevronRight, MoreHorizontal } from "lucide-react-native";

import { NutritionEntityCard } from "@/components/nutrition";
import { MealPanels, type MealPanelItem } from "@/components/panels";
import { EntityCardAction } from "@/components/ui";
import { tokens } from "@/design/tokens";
import type { LibraryWeekPanelItem } from "@/api/types";

const meals: MealPanelItem[] = [
  {
    calorieShare: 27,
    calories: 560,
    carbsAllocation: 52,
    carbsGrams: 72,
    fatAllocation: 22,
    fatGrams: 14,
    foods: [
      { name: "Avena", quantity: 80, quantityUnit: "g" },
      { name: "Yogur griego", quantity: 180, quantityUnit: "g" },
      { name: "Arándanos", quantity: 100, quantityUnit: "g" },
    ],
    id: "program-breakfast",
    name: "Desayuno",
    proteinAllocation: 26,
    proteinGrams: 36,
    time: "08:00",
  },
  {
    calorieShare: 36,
    calories: 742,
    carbsAllocation: 45,
    carbsGrams: 84,
    fatAllocation: 24,
    fatGrams: 20,
    foods: [
      { name: "Arroz", quantity: 180, quantityUnit: "g" },
      { name: "Pollo", quantity: 170, quantityUnit: "g" },
      { name: "Ensalada", quantity: 140, quantityUnit: "g" },
    ],
    id: "program-lunch",
    name: "Almuerzo",
    proteinAllocation: 31,
    proteinGrams: 58,
    time: "13:30",
  },
  {
    calorieShare: 29,
    calories: 598,
    carbsAllocation: 38,
    carbsGrams: 57,
    fatAllocation: 32,
    fatGrams: 21,
    foods: [
      { name: "Salmón", quantity: 160, quantityUnit: "g" },
      { name: "Papas", quantity: 220, quantityUnit: "g" },
      { name: "Verduras", quantity: 140, quantityUnit: "g" },
    ],
    id: "program-dinner",
    name: "Cena",
    proteinAllocation: 30,
    proteinGrams: 45,
    time: "20:00",
  },
];

function mealPanelItem(item: NonNullable<LibraryWeekPanelItem["days"][number]["meals"]>[number]): MealPanelItem {
  return {
    calorieShare: item.calorie_share,
    calories: item.calories,
    carbsAllocation: item.carbs_allocation,
    carbsGrams: item.carbs_grams,
    fatAllocation: item.fat_allocation,
    fatGrams: item.fat_grams,
    foods: item.foods.map((food) => ({ name: food.name, quantity: food.quantity, quantityUnit: food.quantity_unit })),
    id: item.id,
    name: item.name,
    proteinAllocation: item.protein_allocation,
    proteinGrams: item.protein_grams,
    time: item.time?.slice(0, 5),
  };
}

export function ProgramDailyPlanPreview({ day, dayLabel, week }: { day?: LibraryWeekPanelItem["days"][number]; dayLabel: string; week: number }) {
  const router = useRouter();
  const nutrition = day?.nutrition;
  return (
    <NutritionEntityCard
      actions={(
        <>
          <EntityCardAction label={`Más acciones para el plan de ${dayLabel}`} onPress={() => undefined}>
            <MoreHorizontal color={tokens.color.textMuted} size={20} />
          </EntityCardAction>
          {day?.dailyplan_id ? (
            <EntityCardAction
              label={`Ir al detalle del plan de ${dayLabel}`}
              onPress={() => router.push(`/libraries/daily-plans/${day.dailyplan_id}` as Href)}
              role="link">
              <ChevronRight color={tokens.color.textMuted} size={21} />
            </EntityCardAction>
          ) : null}
        </>
      )}
      kpiVariant="nested"
      entity="dailyPlan"
      eyebrow={`SEMANA ${week} · ${dayLabel.toUpperCase()}`}
      indicators={[
        { icon: "dailyPlan", label: "plan asignado", value: 1 },
      ]}
      nutrition={nutrition ? {
        calories: nutrition.calories,
        carbs: nutrition.carbs,
        fat: nutrition.fat,
        protein: { ...nutrition.protein, perKilogram: nutrition.protein.per_kilogram },
      } : {
        calories: 2040,
        carbs: { allocation: 45, grams: 224 },
        fat: { allocation: 26, grams: 59 },
        protein: { allocation: 29, grams: 148, perKilogram: 1.8 },
      }}
      subtitle="Plan diario asignado"
      title={day?.plan_name ?? "Día de entrenamiento"}>
      <MealPanels items={day ? (day.meals ?? []).map(mealPanelItem) : meals} />
    </NutritionEntityCard>
  );
}
