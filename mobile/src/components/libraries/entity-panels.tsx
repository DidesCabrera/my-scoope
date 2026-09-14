import { type Href, useRouter } from "expo-router";
import { ChevronRight, Trash2 } from "lucide-react-native";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import type { LibraryFoodPanelItem, LibraryMealPanelItem, LibraryWeekPanelItem, MealExecutionItem } from "@/api/types";
import { MealCompletionToggleCard } from "@/components/calendarization/meal-adherence-check-in";
import { NutritionEntityCard } from "@/components/nutrition/nutrition-entity-card";
import {
  FoodPanels as SharedFoodPanels,
  type FoodPanelItem,
  MealPanels as SharedMealPanels,
  type MealPanelItem,
  NutritionAllocationPanel,
  NutritionCaloriesPanel,
  NutritionDistributionPanel,
  NutritionMacrosPanel,
} from "@/components/panels";
import { EntityCardAction } from "@/components/ui";
import { tokens } from "@/design/tokens";

import { EntityPanelTabs, PanelBody, PanelEmptyState, PanelSurface } from "@/components/panels/panel-surface";
import { ContextCardActions, type ContextCardAction } from "./context-card-actions";

function toFoodPanelItem(item: LibraryFoodPanelItem): FoodPanelItem {
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

function toMealPanelItem(item: LibraryMealPanelItem): MealPanelItem {
  return {
    id: item.id,
    relationId: item.relation_id,
    detailId: item.detail_id,
    name: item.name,
    time: item.time?.slice(0, 5),
    note: item.note,
    foods: item.foods.map(({ name, quantity, quantity_unit }) => ({ name, quantity, quantityUnit: quantity_unit })),
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

export function FoodPanels({ items }: { items: LibraryFoodPanelItem[] }) {
  return <SharedFoodPanels items={items.map(toFoodPanelItem)} />;
}

export function MealPanels({ items }: { items: LibraryMealPanelItem[] }) {
  return <SharedMealPanels items={items.map(toMealPanelItem)} />;
}

type PinnedTracking = {
  completionError: { mealKey: string; message: string } | null;
  mealExecution: MealExecutionItem[];
  onToggleCompleted(mealKey: string, completed: boolean): void;
  onTogglePrepared(mealKey: string, foodKey: string): void;
  savingMealKey: string | null;
};

export function DailyPlanMealCards({ dailyPlanId, items, onRemove, pinnedTracking }: { dailyPlanId: number; items: LibraryMealPanelItem[]; onRemove?: (item: LibraryMealPanelItem) => Promise<void>; pinnedTracking?: PinnedTracking }) {
  const router = useRouter();
  return (
    <View style={styles.mealCardList}>
      {items.map((item, index) => {
        const execution = pinnedTracking?.mealExecution.find((entry) => entry.meal_key === item.id);
        return <View key={item.id}>
          <NutritionEntityCard
            actions={<>
              {onRemove ? <ContextCardActions
                actions={[{
                  confirmation: {
                    confirmLabel: "Quitar comida",
                    message: "Se quitará esta comida del plan diario. La comida seguirá disponible en tu biblioteca.",
                    title: "¿Quitar comida?",
                  },
                  destructive: true,
                  icon: Trash2,
                  key: "remove",
                  label: "Quitar comida",
                  onPress: () => onRemove(item),
                }] satisfies ContextCardAction[]}
                label={`Más acciones para ${item.name}`}
                title={item.name}
              /> : null}
              <EntityCardAction label={`Ver detalle de ${item.name}`} onPress={() => router.push({ pathname: "/libraries/meals/[id]", params: { dailyPlanId: String(dailyPlanId), dailyPlanMealId: String(item.relation_id ?? ""), id: String(item.detail_id), mealTime: item.time?.slice(0, 5) ?? "", ...(pinnedTracking ? { pinned: "1", mealKey: item.id } : {}) } } as Href)} role="link"><ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} /></EntityCardAction>
            </>}
            beforeNutrition={pinnedTracking ? <MealCompletionToggleCard completed={execution?.status === "completed"} error={pinnedTracking.completionError?.mealKey === item.id ? pinnedTracking.completionError.message : null} onToggle={(completed) => pinnedTracking.onToggleCompleted(item.id, completed)} saving={pinnedTracking.savingMealKey != null} /> : undefined}
            completion={pinnedTracking ? { noteCount: execution?.note.trim() ? 1 : 0 } : undefined}
            entity="meal"
            eyebrow={`Comida ${index + 1}`}
            indicators={[
              { icon: "food", label: "alimentos", value: item.foods.length },
              ...(item.time ? [{ icon: "clock" as const, iconPosition: "leading" as const, label: "hora", tone: "surfaceCard" as const, value: item.time.slice(0, 5) }] : []),
            ]}
            nutrition={{
              calories: item.calories,
              protein: { grams: item.protein_grams, allocation: item.protein_allocation, perKilogram: item.protein_per_kilogram },
              carbs: { grams: item.carbs_grams, allocation: item.carbs_allocation },
              fat: { grams: item.fat_grams, allocation: item.fat_allocation },
            }}
            title={item.name}>
            <SharedFoodPanels items={item.foods.map(toFoodPanelItem)} preparation={pinnedTracking ? {
              isPrepared: (food) => execution?.prepared_food_keys.includes(food.id) ?? false,
              onToggle: (food) => pinnedTracking.onTogglePrepared(item.id, food.id),
            } : undefined} />
          </NutritionEntityCard>
        </View>;
      })}
    </View>
  );
}

export function ProgramPanels({ items }: { items: LibraryWeekPanelItem[] }) {
  const [activeTab, setActiveTab] = useState<"days" | "calories" | "macros" | "distribution" | "allocation">("days");
  const normalized: FoodPanelItem[] = items.map((week) => {
    const ppkValues = week.days.flatMap((day) => day.nutrition?.protein.per_kilogram == null ? [] : [day.nutrition.protein.per_kilogram]);
    return { id: week.id, name: `Semana ${week.week_number}`, quantity: 0, quantityUnit: "", calories: week.calories, calorieShare: week.calorie_share ?? 0, proteinGrams: week.protein_grams, proteinPerKilogram: ppkValues.length ? ppkValues.reduce((sum, value) => sum + value, 0) / ppkValues.length : null, carbsGrams: week.carbs_grams, fatGrams: week.fat_grams, proteinAllocation: week.protein_allocation, carbsAllocation: week.carbs_allocation, fatAllocation: week.fat_allocation };
  });
  return (
    <PanelSurface>
      <EntityPanelTabs<"days" | "calories" | "macros" | "distribution" | "allocation"> activeTab={activeTab} onChange={setActiveTab} tabs={[{ key: "days", label: "Días" }, { key: "calories", label: "Calorías" }, { key: "macros", label: "Macros" }, { key: "distribution", label: "Dist" }, { key: "allocation", label: "Alloc" }]} />
      {items.length === 0 ? <PanelEmptyState label="Todavía no hay semanas configuradas." /> : null}
      {items.length > 0 && activeTab === "days" ? <PanelBody>{items.map((week, index) => <View key={week.id} style={[styles.weekRow, index === items.length - 1 && styles.rowLast]}><Text style={styles.weekTitle}>Semana {week.week_number}</Text>{week.days.map((day) => <Text key={day.day_label} style={styles.weekDay}><Text style={styles.weekDayLabel}>{day.day_label} · </Text>{day.plan_name ?? "Sin plan"}</Text>)}</View>)}</PanelBody> : null}
      {activeTab === "calories" ? <NutritionCaloriesPanel items={normalized} leadingLabel="Semana" /> : null}
      {activeTab === "macros" ? <NutritionMacrosPanel items={normalized} leadingLabel="Semana" /> : null}
      {activeTab === "distribution" ? <NutritionDistributionPanel items={normalized} leadingLabel="Semana" /> : null}
      {activeTab === "allocation" ? <NutritionAllocationPanel items={normalized} leadingLabel="Semana" /> : null}
    </PanelSurface>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", minHeight: 44, paddingHorizontal: tokens.spacing.sm },
  rowLast: { borderBottomWidth: 0 },
  mealCardList: { gap: tokens.spacing.lg, minWidth: 0, width: "100%" },
  pressed: { opacity: 0.6 },
  weekRow: { borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, gap: tokens.spacing.xs, padding: tokens.spacing.md },
  weekTitle: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: "600", marginBottom: tokens.spacing.xs },
  weekDay: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  weekDayLabel: { color: tokens.color.textMain, fontWeight: "600" },
});
