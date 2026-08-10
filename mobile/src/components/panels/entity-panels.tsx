import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { PanelAllocationBar } from "@/components/nutrition";
import { EntityIcon } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { EntityPanelTabs, PanelBody, PanelEmptyState, PanelSurface } from "./panel-surface";

type NutritionPanelValues = {
  calories: number;
  calorieShare: number;
  proteinGrams: number;
  carbsGrams: number;
  fatGrams: number;
  proteinAllocation: number;
  carbsAllocation: number;
  fatAllocation: number;
};

export type FoodPanelItem = NutritionPanelValues & {
  id: string;
  name: string;
  quantity: number;
  quantityUnit: string;
};

export type MealPanelItem = NutritionPanelValues & {
  foods: MealMenuFood[];
  id: string;
  name: string;
  time?: string;
};

export type MealMenuFood = {
  name: string;
  quantity: number;
  quantityUnit: string;
};

type FoodPanelTab = "quantity" | "macros" | "allocation";
type MealPanelTab = "menu" | "macros" | "allocation";

const foodTabs = [
  { key: "quantity", label: "Alimentos" },
  { key: "macros", label: "Macros" },
  { key: "allocation", label: "Alloc" },
] satisfies { key: FoodPanelTab; label: string }[];

const mealTabs = [
  { key: "menu", label: "Menú" },
  { key: "macros", label: "Macros" },
  { key: "allocation", label: "Alloc" },
] satisfies { key: MealPanelTab; label: string }[];

function rounded(value: number): string {
  return Number.isFinite(value) ? Math.round(value).toString() : "0";
}

function decimal(value: number): string {
  return Number.isFinite(value) ? value.toLocaleString("es-CL", { maximumFractionDigits: 1 }) : "0";
}

function QuantityHeader({ leadingLabel, trailingLabel }: { leadingLabel: string; trailingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <Text style={[styles.headerText, styles.name]}>{leadingLabel}</Text>
      <Text style={[styles.headerText, styles.quantityValue]}>{trailingLabel}</Text>
    </View>
  );
}

function MacrosHeader({ leadingLabel }: { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <Text style={[styles.headerText, styles.name]}>{leadingLabel}</Text>
      <Text style={[styles.headerText, styles.kcalCell]}>Kcal</Text>
      {(["P", "C", "F"] as const).map((label) => <Text key={label} style={[styles.headerText, styles.macroValue]}>{label}</Text>)}
    </View>
  );
}

function AllocationHeader({ leadingLabel }: { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header, styles.allocationRow]}>
      <Text style={[styles.headerText, styles.name]}>{leadingLabel}</Text>
      {(["P%", "C%", "F%"] as const).map((label) => <Text key={label} style={[styles.headerText, styles.allocationCell]}>{label}</Text>)}
    </View>
  );
}

export function FoodQuantityPanel({ items }: { items: FoodPanelItem[] }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay alimentos." />;
  return (
    <PanelBody>
      <QuantityHeader leadingLabel="Alimentos" trailingLabel="Qty" />
      {items.map((item) => (
        <View key={item.id} style={styles.row}>
          <Text numberOfLines={2} style={[styles.cell, styles.name]}>{item.name}</Text>
          <Text style={[styles.cell, styles.quantityValue]}>{decimal(item.quantity)} {item.quantityUnit}</Text>
        </View>
      ))}
    </PanelBody>
  );
}

export function NutritionMacrosPanel({ items, leadingLabel }: { items: (FoodPanelItem | MealPanelItem)[]; leadingLabel: string }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay datos nutricionales." />;
  return (
    <PanelBody>
      <MacrosHeader leadingLabel={leadingLabel} />
      {items.map((item) => (
        <View key={item.id} style={styles.row}>
          <Text numberOfLines={2} style={[styles.cell, styles.name]}>{item.name}</Text>
          <View style={styles.kcalCell}>
            <PanelAllocationBar accessibilityLabel={`${item.name}: ${rounded(item.calories)} calorías`} displayValue={rounded(item.calories)} size="compact" tone="calories" value={item.calorieShare} />
          </View>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.proteinGrams)}</Text>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.carbsGrams)}</Text>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.fatGrams)}</Text>
        </View>
      ))}
    </PanelBody>
  );
}

export function NutritionAllocationPanel({ items, leadingLabel }: { items: (FoodPanelItem | MealPanelItem)[]; leadingLabel: string }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay distribución nutricional." />;
  return (
    <PanelBody>
      <AllocationHeader leadingLabel={leadingLabel} />
      {items.map((item) => (
        <View key={item.id} style={[styles.row, styles.allocationRow]}>
          <Text numberOfLines={2} style={[styles.cell, styles.name]}>{item.name}</Text>
          <PanelAllocationBar size="compact" style={styles.allocationCell} tone="protein" value={item.proteinAllocation} />
          <PanelAllocationBar size="compact" style={styles.allocationCell} tone="carbs" value={item.carbsAllocation} />
          <PanelAllocationBar size="compact" style={styles.allocationCell} tone="fat" value={item.fatAllocation} />
        </View>
      ))}
    </PanelBody>
  );
}

export function MealMenuPanel({ items }: { items: MealPanelItem[] }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay comidas." />;
  return (
    <PanelBody>
      {items.map((item) => (
        <View key={item.id} style={styles.menuRow}>
          <View style={styles.menuTitleRow}>
            <EntityIcon entity="meal" size="compact" />
            <Text numberOfLines={2} style={styles.menuName}>{item.name}</Text>
            {item.time ? <Text style={styles.menuTime}>{item.time}</Text> : null}
          </View>
          <Text style={styles.menuFoods}>
            {item.foods.map((food) => `${food.name} (${decimal(food.quantity)}${food.quantityUnit})`).join(", ")}
          </Text>
        </View>
      ))}
    </PanelBody>
  );
}

export function FoodPanels({ items }: { items: FoodPanelItem[] }) {
  const [activeTab, setActiveTab] = useState<FoodPanelTab>("quantity");
  return (
    <PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={foodTabs} />
      {activeTab === "quantity" ? <FoodQuantityPanel items={items} /> : null}
      {activeTab === "macros" ? <NutritionMacrosPanel items={items} leadingLabel="Alimentos" /> : null}
      {activeTab === "allocation" ? <NutritionAllocationPanel items={items} leadingLabel="Alimentos" /> : null}
    </PanelSurface>
  );
}

export function MealPanels({ items }: { items: MealPanelItem[] }) {
  const [activeTab, setActiveTab] = useState<MealPanelTab>("menu");
  return (
    <PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={mealTabs} />
      {activeTab === "menu" ? <MealMenuPanel items={items} /> : null}
      {activeTab === "macros" ? <NutritionMacrosPanel items={items} leadingLabel="Comidas" /> : null}
      {activeTab === "allocation" ? <NutritionAllocationPanel items={items} leadingLabel="Comidas" /> : null}
    </PanelSurface>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", minHeight: 44 },
  header: { minHeight: 32 },
  headerText: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.semibold, letterSpacing: 0, textAlign: "center", textTransform: "uppercase" },
  cell: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0 },
  name: { flex: 1, minWidth: 0, paddingHorizontal: tokens.spacing.xs, textAlign: "left" },
  quantityValue: { textAlign: "right", width: 88 },
  kcalCell: { width: 58 },
  macroValue: { textAlign: "center", width: 34 },
  allocationRow: { gap: 3 },
  allocationCell: { flex: 1, minWidth: 0, width: "auto" },
  menuRow: { borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, gap: tokens.spacing.compact, paddingHorizontal: tokens.spacing.xs, paddingVertical: tokens.spacing.md },
  menuTitleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  menuName: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 18 },
  menuTime: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.regular, letterSpacing: 0 },
  menuFoods: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0, lineHeight: 20, opacity: 0.82 },
});
