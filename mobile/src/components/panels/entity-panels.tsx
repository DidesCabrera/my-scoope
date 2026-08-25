import { useState } from "react";
import { ChevronRight } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { MacroCalorieDistribution, PanelAllocationBar } from "@/components/nutrition";
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
  detailId?: number;
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

type FoodPanelTab = "quantity" | "calories" | "macros" | "allocation";
type MealPanelTab = "menu" | "calories" | "macros" | "allocation";

const foodTabs = [
  { key: "quantity", label: "Alimentos" },
  { key: "calories", label: "Calorías" },
  { key: "macros", label: "Macros" },
  { key: "allocation", label: "Alloc" },
] satisfies { key: FoodPanelTab; label: string }[];

const mealTabs = [
  { key: "menu", label: "Menú" },
  { key: "calories", label: "Calorías" },
  { key: "macros", label: "Macros" },
  { key: "allocation", label: "Alloc" },
] satisfies { key: MealPanelTab; label: string }[];

function rounded(value: number): string {
  return Number.isFinite(value) ? Math.round(value).toString() : "0";
}

function decimal(value: number): string {
  return Number.isFinite(value) ? value.toLocaleString("es-CL", { maximumFractionDigits: 1 }) : "0";
}

export function MealRowIdentity({ name }: { name: string }) {
  return (
    <View style={styles.mealIdentity}>
      <EntityIcon entity="meal" size="compact" />
      <Text numberOfLines={2} style={styles.mealIdentityName}>{name}</Text>
    </View>
  );
}

function isMealPanelItem(item: FoodPanelItem | MealPanelItem): item is MealPanelItem {
  return "foods" in item;
}

function PanelItemName({ item }: { item: FoodPanelItem | MealPanelItem }) {
  return (
    <View style={styles.gridLeadingCell}>
      {isMealPanelItem(item) ? <MealRowIdentity name={item.name} /> : <Text numberOfLines={2} style={[styles.cell, styles.name]}>{item.name}</Text>}
    </View>
  );
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
      <Text style={[styles.headerText, styles.name, styles.gridLeadingCell]}>{leadingLabel}</Text>
      {(["P", "C", "F"] as const).map((label) => <Text key={label} style={[styles.headerText, styles.macroValue]}>{label}</Text>)}
      <Text style={[styles.headerText, styles.distributionCell]}>P|C|F%</Text>
    </View>
  );
}

function CaloriesHeader({ leadingLabel }: { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <Text style={[styles.headerText, styles.name, styles.gridLeadingCell]}>{leadingLabel}</Text>
      <Text style={[styles.headerText, styles.calorieValue]}>Cal</Text>
      <Text style={[styles.headerText, styles.calorieShare]}>% Cal</Text>
    </View>
  );
}

function AllocationHeader({ leadingLabel }: { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header, styles.allocationRow]}>
      <Text style={[styles.headerText, styles.name, styles.gridLeadingCell]}>{leadingLabel}</Text>
      {(["P%", "C%", "F%"] as const).map((label) => <Text key={label} style={[styles.headerText, styles.allocationCell]}>{label}</Text>)}
    </View>
  );
}

export function FoodQuantityPanel({ items }: { items: FoodPanelItem[] }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay alimentos." />;
  return (
    <PanelBody>
      <QuantityHeader leadingLabel="Alimentos" trailingLabel="Qty" />
      {items.map((item, index) => (
        <View key={item.id} style={[styles.row, index === items.length - 1 && styles.rowLast]}>
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
      {items.map((item, index) => (
        <View key={item.id} style={[styles.row, index === items.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} />
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.proteinGrams)}</Text>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.carbsGrams)}</Text>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.fatGrams)}</Text>
          <MacroCalorieDistribution
            carbsGrams={item.carbsGrams}
            fatGrams={item.fatGrams}
            proteinGrams={item.proteinGrams}
            style={styles.distributionCell}
          />
        </View>
      ))}
    </PanelBody>
  );
}

export function NutritionCaloriesPanel({ items, leadingLabel }: { items: (FoodPanelItem | MealPanelItem)[]; leadingLabel: string }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay datos calóricos." />;
  return (
    <PanelBody>
      <CaloriesHeader leadingLabel={leadingLabel} />
      {items.map((item, index) => (
        <View key={item.id} style={[styles.row, index === items.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} />
          <Text style={[styles.cell, styles.calorieValue]}>{rounded(item.calories)}</Text>
          <View style={styles.calorieShare}>
            <PanelAllocationBar accessibilityLabel={`${item.name}: ${rounded(item.calorieShare)}% de las calorías`} tone="calories" value={item.calorieShare} />
          </View>
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
      {items.map((item, index) => (
        <View key={item.id} style={[styles.row, styles.allocationRow, index === items.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} />
          <PanelAllocationBar style={styles.allocationCell} tone="protein" value={item.proteinAllocation} />
          <PanelAllocationBar style={styles.allocationCell} tone="carbs" value={item.carbsAllocation} />
          <PanelAllocationBar style={styles.allocationCell} tone="fat" value={item.fatAllocation} />
        </View>
      ))}
    </PanelBody>
  );
}

export function MealMenuPanel({ items, onOpenItem }: { items: MealPanelItem[]; onOpenItem?: (item: MealPanelItem) => void }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay comidas." />;
  return (
    <PanelBody>
      {items.map((item, index) => (
        <View key={item.id} style={[styles.menuRow, index === items.length - 1 && styles.rowLast]}>
          <View style={styles.menuCopy}>
            <View style={styles.menuTitleRow}>
              <MealRowIdentity name={item.name} />
              {item.time ? <Text style={styles.menuTime}>{item.time}</Text> : null}
            </View>
            <Text style={styles.menuFoods}>
              {item.foods.map((food) => `${food.name} (${decimal(food.quantity)}${food.quantityUnit})`).join(", ")}
            </Text>
          </View>
          {item.detailId != null && onOpenItem ? (
            <Pressable
              accessibilityLabel={`Ver detalle de ${item.name}`}
              accessibilityRole="link"
              hitSlop={8}
              onPress={() => onOpenItem(item)}
              style={({ pressed }) => [styles.menuAction, pressed && styles.menuActionPressed]}>
              <ChevronRight color={tokens.color.textMuted} size={21} strokeWidth={2.2} />
            </Pressable>
          ) : null}
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
      {activeTab === "calories" ? <NutritionCaloriesPanel items={items} leadingLabel="Alimentos" /> : null}
      {activeTab === "macros" ? <NutritionMacrosPanel items={items} leadingLabel="Alimentos" /> : null}
      {activeTab === "allocation" ? <NutritionAllocationPanel items={items} leadingLabel="Alimentos" /> : null}
    </PanelSurface>
  );
}

export function MealPanels({ items, onOpenItem }: { items: MealPanelItem[]; onOpenItem?: (item: MealPanelItem) => void }) {
  const [activeTab, setActiveTab] = useState<MealPanelTab>("menu");
  return (
    <PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={mealTabs} />
      {activeTab === "menu" ? <MealMenuPanel items={items} onOpenItem={onOpenItem} /> : null}
      {activeTab === "calories" ? <NutritionCaloriesPanel items={items} leadingLabel="Comidas" /> : null}
      {activeTab === "macros" ? <NutritionMacrosPanel items={items} leadingLabel="Comidas" /> : null}
      {activeTab === "allocation" ? <NutritionAllocationPanel items={items} leadingLabel="Comidas" /> : null}
    </PanelSurface>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", minHeight: 44, paddingHorizontal: tokens.spacing.sm },
  rowLast: { borderBottomWidth: 0 },
  header: { minHeight: 32 },
  headerText: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.semibold, letterSpacing: 0, textAlign: "center", textTransform: "uppercase" },
  cell: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0 },
  name: { flex: 1, minWidth: 0, paddingHorizontal: tokens.spacing.xs, textAlign: "left" },
  gridLeadingCell: { flexBasis: "40%", flexGrow: 0, flexShrink: 0, minWidth: 0 },
  quantityValue: { textAlign: "right", width: 88 },
  macroValue: { flex: 1, minWidth: 0, textAlign: "center" },
  distributionCell: { flex: 1.4, minWidth: 0 },
  calorieValue: { textAlign: "center", width: 54 },
  calorieShare: { flex: 1, minWidth: 92, textAlign: "center" },
  allocationRow: { gap: 3 },
  allocationCell: { flex: 1, minWidth: 0, width: "auto" },
  menuRow: { alignItems: "center", alignSelf: "stretch", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.compact, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.md },
  menuCopy: { flex: 1, gap: tokens.spacing.compact, minWidth: 0 },
  menuAction: { alignItems: "center", alignSelf: "stretch", borderRadius: tokens.radius.pill, justifyContent: "center", minWidth: 32 },
  menuActionPressed: { opacity: 0.55 },
  menuTitleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  mealIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0, paddingHorizontal: tokens.spacing.xs },
  mealIdentityName: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 18 },
  menuTime: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.regular, letterSpacing: 0, paddingHorizontal: tokens.spacing.xs },
  menuFoods: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0, lineHeight: 20, opacity: 0.82, paddingHorizontal: tokens.spacing.xs },
});
