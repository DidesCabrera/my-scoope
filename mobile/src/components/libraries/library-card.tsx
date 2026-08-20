import { type Href, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { Alert, Pressable, StyleSheet } from "react-native";
import type { LibraryItem } from "@/api/types";
import { NutritionEntityCard } from "@/components/nutrition";
import { tokens } from "@/design/tokens";

import { FoodPanels, MealPanels, ProgramPanels } from "./entity-panels";
import { libraryNutrition } from "./presentation-adapters";
import { ProgramChildCard, type ProgramMetricDatum } from "./program-child-card";

function indicatorValue(item: LibraryItem, icon: "week" | "dailyPlan" | "food"): number {
  const value = item.indicators.find((indicator) => indicator.icon === icon)?.value;
  return typeof value === "number" ? value : Number.parseInt(String(value ?? 0), 10) || 0;
}

function programMetricData(item: LibraryItem): ProgramMetricDatum[] {
  if (item.panel.kind !== "weeks") return [];
  return item.panel.weeks.map((week) => {
    const filledDays = week.filled_days_count ?? week.days.filter((day) => day.plan_name).length;
    const ppkValues = week.days.map((day) => day.nutrition?.protein.per_kilogram).filter((value): value is number => value != null);
    return {
      allocation: { protein: week.protein_allocation, carbs: week.carbs_allocation, fat: week.fat_allocation },
      calories: week.average_calories ?? week.calories / Math.max(filledDays, 1),
      carbs: week.carbs_grams / Math.max(filledDays, 1),
      fat: week.fat_grams / Math.max(filledDays, 1),
      protein: week.protein_grams / Math.max(filledDays, 1),
      ppk: ppkValues.length ? ppkValues.reduce((sum, value) => sum + value, 0) / ppkValues.length : null,
    };
  });
}

export function LibraryCard({ item }: { item: LibraryItem }) {
  const router = useRouter();
  const segment = item.entity === "dailyPlan" ? "daily-plans" : item.entity === "program" ? "programs" : item.entity === "meal" ? "meals" : "foods";
  const detailHref = `/libraries/${segment}/${item.id}` as Href;
  if (item.entity === "program") {
    const metrics = programMetricData(item);
    return (
      <ProgramChildCard
        axisLabels={metrics.map((_, index) => `SEMANA ${index + 1}`)}
        filledDaysCount={indicatorValue(item, "dailyPlan")}
        foodsCount={indicatorValue(item, "food")}
        metricData={metrics}
        onMore={() => Alert.alert(item.name, "Las acciones de edición estarán disponibles desde el detalle del programa.")}
        onOpen={() => router.push(detailHref)}
        owner={item.creator}
        title={item.name}
        weeksCount={indicatorValue(item, "week")}
      />
    );
  }
  return (
    <NutritionEntityCard entity={item.entity} indicators={item.indicators} nutrition={libraryNutrition(item.nutrition)} subtitle={item.subtitle || undefined} title={item.name}>
      {item.panel.kind === "foods" ? <FoodPanels items={item.panel.foods} /> : null}
      {item.panel.kind === "meals" ? <MealPanels items={item.panel.meals} /> : null}
      {item.panel.kind === "weeks" ? <ProgramPanels items={item.panel.weeks} /> : null}
      <Pressable accessibilityLabel={`Ver detalle de ${item.name}`} accessibilityRole="button" hitSlop={8} onPress={() => router.push(detailHref)} style={({ pressed }) => [styles.detailButton, pressed && styles.pressed]}>
        <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
      </Pressable>
    </NutritionEntityCard>
  );
}

const styles = StyleSheet.create({
  detailButton: { alignItems: "center", alignSelf: "flex-end", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  pressed: { opacity: 0.6 },
});
