import { MoreHorizontal } from "lucide-react-native";
import { Pressable, StyleSheet } from "react-native";

import { NutritionEntityCard } from "@/components/nutrition";
import { MealPanels, type MealPanelItem } from "@/components/panels";
import { tokens } from "@/design/tokens";

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

export function ProgramDailyPlanPreview({ dayLabel, week }: { dayLabel: string; week: number }) {
  return (
    <NutritionEntityCard
      accessory={(
        <Pressable accessibilityLabel={`Más acciones para el plan de ${dayLabel}`} accessibilityRole="button" style={({ pressed }) => [styles.action, pressed && styles.pressed]}>
          <MoreHorizontal color={tokens.color.textMuted} size={20} />
        </Pressable>
      )}
      density="compact"
      entity="dailyPlan"
      eyebrow={`SEMANA ${week} · ${dayLabel.toUpperCase()}`}
      indicators={[
        { icon: "meal", label: "comidas", value: 3 },
        { icon: "food", label: "alimentos", value: 9 },
      ]}
      nutrition={{
        calories: 2040,
        carbs: { allocation: 45, grams: 224 },
        fat: { allocation: 26, grams: 59 },
        protein: { allocation: 29, grams: 148, perKilogram: 1.8 },
      }}
      subtitle="Plan diario asignado"
      title="Día de entrenamiento">
      <MealPanels items={meals} />
    </NutritionEntityCard>
  );
}

const styles = StyleSheet.create({
  action: { alignItems: "center", borderRadius: tokens.radius.pill, height: 34, justifyContent: "center", width: 34 },
  pressed: { opacity: 0.68 },
});
