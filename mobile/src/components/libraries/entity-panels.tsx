import { type Href, useRouter } from "expo-router";
import { ChevronRight, Trash2 } from "lucide-react-native";
import { useState } from "react";
import { type StyleProp, StyleSheet, Text, View, type ViewStyle } from "react-native";

import type { LibraryFoodPanelItem, LibraryMealPanelItem, LibraryWeekPanelItem } from "@/api/types";
import { PanelAllocationBar } from "@/components/nutrition/allocation-bar";
import { CalorieDistributionBar } from "@/components/nutrition/calorie-distribution-bar";
import { NutritionEntityCard } from "@/components/nutrition/nutrition-entity-card";
import { EntityCardAction, EntityIcon } from "@/components/ui";
import { tokens } from "@/design/tokens";

import { EntityPanelTabs, PanelBody, PanelEmptyState, PanelSurface } from "@/components/panels/panel-surface";
import { ContextCardActions, type ContextCardAction } from "./context-card-actions";

type PanelNutritionItem = {
  id: string;
  name: string;
  calories: number;
  calorieShare: number;
  calorieDistribution: LibraryFoodPanelItem["calorie_distribution"];
  proteinGrams: number;
  carbsGrams: number;
  fatGrams: number;
  proteinAllocation: number;
  carbsAllocation: number;
  fatAllocation: number;
};

function decimal(value: number): string {
  return Number.isFinite(value) ? value.toLocaleString("es-CL", { maximumFractionDigits: 1 }) : "0";
}

function rounded(value: number): string {
  return Number.isFinite(value) ? Math.round(value).toString() : "0";
}

function calorieDistribution(distribution: LibraryFoodPanelItem["calorie_distribution"] | undefined, protein: number, carbs: number, fat: number) {
  if (distribution) return distribution;
  const proteinCalories = protein * 4;
  const carbsCalories = carbs * 4;
  const fatCalories = fat * 9;
  const total = proteinCalories + carbsCalories + fatCalories;
  if (total <= 0) return { protein: 0, carbs: 0, fat: 0 };
  return { protein: proteinCalories / total * 100, carbs: carbsCalories / total * 100, fat: fatCalories / total * 100 };
}

function normalizeFood(item: LibraryFoodPanelItem): PanelNutritionItem {
  return { id: item.id, name: item.name, calories: item.calories, calorieShare: item.calorie_share, calorieDistribution: calorieDistribution(item.calorie_distribution, item.protein_grams, item.carbs_grams, item.fat_grams), proteinGrams: item.protein_grams, carbsGrams: item.carbs_grams, fatGrams: item.fat_grams, proteinAllocation: item.protein_allocation, carbsAllocation: item.carbs_allocation, fatAllocation: item.fat_allocation };
}

function normalizeMeal(item: LibraryMealPanelItem): PanelNutritionItem {
  return { id: item.id, name: item.name, calories: item.calories, calorieShare: item.calorie_share, calorieDistribution: calorieDistribution(item.calorie_distribution, item.protein_grams, item.carbs_grams, item.fat_grams), proteinGrams: item.protein_grams, carbsGrams: item.carbs_grams, fatGrams: item.fat_grams, proteinAllocation: item.protein_allocation, carbsAllocation: item.carbs_allocation, fatAllocation: item.fat_allocation };
}

function PanelItemName({ item, meal = false, style }: { item: PanelNutritionItem; meal?: boolean; style: StyleProp<ViewStyle> }) {
  return (
    <View style={style}>
      {meal ? (
        <View style={styles.mealIdentity}>
          <EntityIcon entity="meal" size="compact" />
          <Text numberOfLines={2} style={styles.mealIdentityName}>{item.name}</Text>
        </View>
      ) : <Text numberOfLines={2} style={styles.itemName}>{item.name}</Text>}
    </View>
  );
}

function MacrosPanel({ items, leadingLabel, meal = false }: { items: PanelNutritionItem[]; leadingLabel: string; meal?: boolean }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay datos nutricionales." />;
  return (
    <PanelBody>
      <View style={[styles.row, styles.header]}>
        <Text style={[styles.headerText, styles.name, styles.macrosLeadingCell]}>{leadingLabel}</Text>
        {(["P", "C", "F"] as const).map((label) => <Text key={label} style={[styles.headerText, styles.macroCell]}>{label}</Text>)}
        <Text style={[styles.headerText, styles.distributionCell]}>P|C|F%</Text>
      </View>
      {items.map((item, index) => (
        <View key={item.id} style={[styles.row, index === items.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} meal={meal} style={styles.macrosLeadingCell} />
          <Text style={[styles.cell, styles.macroCell]}>{decimal(item.proteinGrams)}</Text>
          <Text style={[styles.cell, styles.macroCell]}>{decimal(item.carbsGrams)}</Text>
          <Text style={[styles.cell, styles.macroCell]}>{decimal(item.fatGrams)}</Text>
          <CalorieDistributionBar distribution={item.calorieDistribution} style={styles.distributionCell} />
        </View>
      ))}
    </PanelBody>
  );
}

function CaloriesPanel({ items, leadingLabel, meal = false }: { items: PanelNutritionItem[]; leadingLabel: string; meal?: boolean }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay información calórica." />;
  return <PanelBody>
    <View style={[styles.row, styles.header, styles.caloriesRow]}><Text style={[styles.headerText, styles.name, styles.caloriesLeadingCell]}>{leadingLabel}</Text><Text style={[styles.headerText, styles.calorieValueCell]}>Cal</Text><Text style={[styles.headerText, styles.calorieShareCell]}>% Cal</Text></View>
    {items.map((item, index) => <View key={item.id} style={[styles.row, styles.caloriesRow, index === items.length - 1 && styles.rowLast]}><PanelItemName item={item} meal={meal} style={styles.caloriesLeadingCell} /><Text style={[styles.cell, styles.calorieValueCell]}>{rounded(item.calories)}</Text><PanelAllocationBar accessibilityLabel={`${item.name}: ${Math.round(item.calorieShare)}% de las calorías`} style={styles.calorieShareCell} tone="calories" value={item.calorieShare} /></View>)}
  </PanelBody>;
}

function AllocationPanel({ items, leadingLabel, meal = false }: { items: PanelNutritionItem[]; leadingLabel: string; meal?: boolean }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay distribución nutricional." />;
  return (
    <PanelBody>
      <View style={[styles.row, styles.header, styles.allocationRow]}>
        <Text style={[styles.headerText, styles.name, styles.allocationLeadingCell]}>{leadingLabel}</Text>
        {(["P%", "C%", "F%"] as const).map((label) => <Text key={label} style={[styles.headerText, styles.allocationCell]}>{label}</Text>)}
      </View>
      {items.map((item, index) => (
        <View key={item.id} style={[styles.row, styles.allocationRow, index === items.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} meal={meal} style={styles.allocationLeadingCell} />
          <PanelAllocationBar style={styles.allocationCell} tone="protein" value={item.proteinAllocation} />
          <PanelAllocationBar style={styles.allocationCell} tone="carbs" value={item.carbsAllocation} />
          <PanelAllocationBar style={styles.allocationCell} tone="fat" value={item.fatAllocation} />
        </View>
      ))}
    </PanelBody>
  );
}

export function FoodPanels({ items }: { items: LibraryFoodPanelItem[] }) {
  const [activeTab, setActiveTab] = useState<"quantity" | "calories" | "macros" | "allocation">("quantity");
  const normalized = items.map(normalizeFood);
  return (
    <PanelSurface>
      <EntityPanelTabs<"quantity" | "calories" | "macros" | "allocation"> activeTab={activeTab} onChange={setActiveTab} tabs={[{ key: "quantity", label: "Alimentos" }, { key: "calories", label: "Calorías" }, { key: "macros", label: "Macros" }, { key: "allocation", label: "Alloc" }]} />
      {activeTab === "quantity" ? (
        items.length > 0 ? <PanelBody><View style={[styles.row, styles.header]}><Text style={[styles.headerText, styles.name]}>Alimentos</Text><Text style={[styles.headerText, styles.quantityValue]}>Cantidad</Text></View>{items.map((item, index) => <View key={item.id} style={[styles.row, index === items.length - 1 && styles.rowLast]}><Text numberOfLines={2} style={[styles.cell, styles.name]}>{item.name}</Text><Text style={[styles.cell, styles.quantityValue]}>{decimal(item.quantity)} {item.quantity_unit}</Text></View>)}</PanelBody> : <PanelEmptyState label="Todavía no hay alimentos." />
      ) : null}
      {activeTab === "calories" ? <CaloriesPanel items={normalized} leadingLabel="Alimentos" /> : null}
      {activeTab === "macros" ? <MacrosPanel items={normalized} leadingLabel="Alimentos" /> : null}
      {activeTab === "allocation" ? <AllocationPanel items={normalized} leadingLabel="Alimentos" /> : null}
    </PanelSurface>
  );
}

export function MealPanels({ items }: { items: LibraryMealPanelItem[] }) {
  const [activeTab, setActiveTab] = useState<"menu" | "calories" | "macros" | "allocation">("menu");
  const normalized = items.map(normalizeMeal);
  return (
    <PanelSurface>
      <EntityPanelTabs<"menu" | "calories" | "macros" | "allocation"> activeTab={activeTab} onChange={setActiveTab} tabs={[{ key: "menu", label: "Menú" }, { key: "calories", label: "Calorías" }, { key: "macros", label: "Macros" }, { key: "allocation", label: "Alloc" }]} />
      {activeTab === "menu" ? (
        items.length > 0 ? <PanelBody>{items.map((item, index) => <View key={item.id} style={[styles.menuRow, index === items.length - 1 && styles.rowLast]}><View style={styles.menuTitleRow}><View style={styles.mealIdentity}><EntityIcon entity="meal" size="compact" /><Text numberOfLines={2} style={styles.mealIdentityName}>{item.name}</Text></View>{item.time ? <Text style={styles.menuTime}>{item.time.slice(0, 5)}</Text> : null}</View><Text style={styles.menuFoods}>{item.foods.map((food) => `${food.name} (${decimal(food.quantity)}${food.quantity_unit})`).join(", ")}</Text></View>)}</PanelBody> : <PanelEmptyState label="Todavía no hay comidas." />
      ) : null}
      {activeTab === "calories" ? <CaloriesPanel items={normalized} leadingLabel="Comidas" meal /> : null}
      {activeTab === "macros" ? <MacrosPanel items={normalized} leadingLabel="Comidas" meal /> : null}
      {activeTab === "allocation" ? <AllocationPanel items={normalized} leadingLabel="Comidas" meal /> : null}
    </PanelSurface>
  );
}

export function DailyPlanMealCards({ items, onRemove }: { items: LibraryMealPanelItem[]; onRemove?: (item: LibraryMealPanelItem) => Promise<void> }) {
  const router = useRouter();
  return (
    <View style={styles.mealCardList}>
      {items.map((item, index) => (
        <View key={item.id}>
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
              <EntityCardAction label={`Ver detalle de ${item.name}`} onPress={() => router.push(`/libraries/meals/${item.detail_id}` as Href)} role="link"><ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} /></EntityCardAction>
            </>}
            entity="meal"
            eyebrow={`Comida ${index + 1}`}
            indicators={[{ icon: "food", label: "alimentos", value: item.foods.length }]}
            nutrition={{
              calories: item.calories,
              protein: { grams: item.protein_grams, allocation: item.protein_allocation, perKilogram: item.protein_per_kilogram },
              carbs: { grams: item.carbs_grams, allocation: item.carbs_allocation },
              fat: { grams: item.fat_grams, allocation: item.fat_allocation },
            }}
            subtitle={item.time ? item.time.slice(0, 5) : undefined}
            title={item.name}>
            <FoodPanels items={item.foods} />
          </NutritionEntityCard>
        </View>
      ))}
    </View>
  );
}

export function ProgramPanels({ items }: { items: LibraryWeekPanelItem[] }) {
  const [activeTab, setActiveTab] = useState<"days" | "calories" | "macros" | "allocation">("days");
  const normalized: PanelNutritionItem[] = items.map((week) => ({ id: week.id, name: `Semana ${week.week_number}`, calories: week.calories, calorieShare: week.calorie_share ?? 0, calorieDistribution: calorieDistribution(week.calorie_distribution, week.protein_grams, week.carbs_grams, week.fat_grams), proteinGrams: week.protein_grams, carbsGrams: week.carbs_grams, fatGrams: week.fat_grams, proteinAllocation: week.protein_allocation, carbsAllocation: week.carbs_allocation, fatAllocation: week.fat_allocation }));
  return (
    <PanelSurface>
      <EntityPanelTabs<"days" | "calories" | "macros" | "allocation"> activeTab={activeTab} onChange={setActiveTab} tabs={[{ key: "days", label: "Días" }, { key: "calories", label: "Calorías" }, { key: "macros", label: "Macros" }, { key: "allocation", label: "Alloc" }]} />
      {items.length === 0 ? <PanelEmptyState label="Todavía no hay semanas configuradas." /> : null}
      {items.length > 0 && activeTab === "days" ? <PanelBody>{items.map((week, index) => <View key={week.id} style={[styles.weekRow, index === items.length - 1 && styles.rowLast]}><Text style={styles.weekTitle}>Semana {week.week_number}</Text>{week.days.map((day) => <Text key={day.day_label} style={styles.weekDay}><Text style={styles.weekDayLabel}>{day.day_label} · </Text>{day.plan_name ?? "Sin plan"}</Text>)}</View>)}</PanelBody> : null}
      {activeTab === "calories" ? <CaloriesPanel items={normalized} leadingLabel="Semana" /> : null}
      {activeTab === "macros" ? <MacrosPanel items={normalized} leadingLabel="Semana" /> : null}
      {activeTab === "allocation" ? <AllocationPanel items={normalized} leadingLabel="Semana" /> : null}
    </PanelSurface>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", minHeight: 44, paddingHorizontal: tokens.spacing.sm },
  rowLast: { borderBottomWidth: 0 },
  header: { minHeight: 32 },
  headerText: { color: tokens.color.textMuted, fontSize: 10, fontWeight: "600", textAlign: "center", textTransform: "uppercase" },
  cell: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: "400" },
  name: { flex: 1, minWidth: 0, paddingHorizontal: tokens.spacing.xs, textAlign: "left" },
  itemName: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: "400", lineHeight: 18, paddingHorizontal: tokens.spacing.xs, textAlign: "left" },
  quantityValue: { textAlign: "right", width: 88 },
  macrosLeadingCell: { alignSelf: "stretch", flex: 1.35, justifyContent: "center", minWidth: 0 },
  macroCell: { flex: 0.42, minWidth: 0, textAlign: "center" },
  distributionCell: { flex: 1.2, minWidth: 0 },
  caloriesRow: { gap: 4 },
  caloriesLeadingCell: { alignSelf: "stretch", flex: 1.6, justifyContent: "center", minWidth: 0 },
  calorieValueCell: { flex: 0.62, minWidth: 0, textAlign: "center" },
  calorieShareCell: { flex: 1, minWidth: 0 },
  allocationRow: { gap: tokens.spacing.sm },
  allocationLeadingCell: { alignSelf: "stretch", flex: 1.6, justifyContent: "center", minWidth: 0 },
  allocationCell: { flex: 1, minWidth: 0, width: "auto" },
  mealIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0, paddingHorizontal: tokens.spacing.xs },
  mealIdentityName: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: "600", lineHeight: 18 },
  menuRow: { alignSelf: "stretch", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, gap: tokens.spacing.compact, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.md },
  menuTitleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  menuTime: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], paddingHorizontal: tokens.spacing.xs },
  menuFoods: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20, opacity: 0.82, paddingHorizontal: tokens.spacing.xs },
  mealCardList: { gap: tokens.spacing.lg, minWidth: 0, width: "100%" },
  pressed: { opacity: 0.6 },
  weekRow: { borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, gap: tokens.spacing.xs, padding: tokens.spacing.md },
  weekTitle: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: "600", marginBottom: tokens.spacing.xs },
  weekDay: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  weekDayLabel: { color: tokens.color.textMain, fontWeight: "600" },
});
