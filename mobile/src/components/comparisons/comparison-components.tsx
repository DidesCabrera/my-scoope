import { ChevronDown, Trash2 } from "lucide-react-native";
import { type PropsWithChildren, type ReactNode, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, useWindowDimensions, View } from "react-native";

import type { ComparisonResultItem } from "@/api/types";
import { PanelAllocationBar } from "@/components/nutrition";
import {
  EntityPanelTabs,
  FoodPanels,
  type FoodPanelItem,
  NutritionAllocationPanel,
  NutritionCaloriesPanel,
  NutritionDistributionPanel,
  NutritionMacrosPanel,
  PanelSurface,
} from "@/components/panels";
import { Button, DistributedTabBar, EntityIcon, SectionHeading, SectionIcon, StructuralIndicators, type EntityKind } from "@/components/ui";
import { tokens } from "@/design/tokens";

export type ComparisonScope = Extract<EntityKind, "food" | "meal" | "dailyPlan">;
export type ComparisonMetricTone = "calories" | "ppk" | "protein" | "carbs" | "fat";
type ComparisonPreviewTab = "allocation" | "calories" | "distribution" | "macros";

const scopeLabels: Record<ComparisonScope, string> = {
  food: "Alimentos",
  meal: "Comidas",
  dailyPlan: "Planes",
};

const scopeSingularLabels: Record<ComparisonScope, string> = {
  food: "Alimento",
  meal: "Comida",
  dailyPlan: "Plan",
};

const metricColors: Record<ComparisonMetricTone, string> = {
  calories: "#7B5B39",
  ppk: tokens.color.ppk,
  protein: tokens.color.protein,
  carbs: tokens.color.carbs,
  fat: tokens.color.fat,
};

const comparisonEntityColors: Record<ComparisonScope, string> = {
  food: tokens.color.food,
  meal: tokens.color.meal,
  dailyPlan: tokens.color.dailyPlan,
};

function entityBorderStyle(entity: ComparisonScope) {
  return { borderTopColor: comparisonEntityColors[entity], borderTopWidth: 3 } as const;
}

function formatComparisonQuantity(value: string): string {
  const normalized = value.trim().replace(/^\(|\)$/g, "").replace(/\s+g$/i, "g");
  return `(${normalized})`;
}

export function ComparisonScopeTabs({ activeScope, onChange }: { activeScope: ComparisonScope; onChange: (scope: ComparisonScope) => void }) {
  return (
    <DistributedTabBar
      accessibilityLabel="Tipo de comparación"
      activeTab={activeScope}
      onChange={onChange}
      tabs={(Object.keys(scopeLabels) as ComparisonScope[]).map((scope) => ({ icon: <EntityIcon entity={scope} size="compact" />, key: scope, label: scopeLabels[scope] }))}
    />
  );
}

function comparisonPanelItems(items: ComparisonResultItem[]): FoodPanelItem[] {
  const totalCalories = items.reduce((sum, item) => sum + item.values.calories, 0);
  return items.map((item) => {
    const macroCalories = (item.values.protein_g * 4) + (item.values.carbs_g * 4) + (item.values.fat_g * 9);
    return {
      calorieShare: totalCalories > 0 ? item.values.calories * 100 / totalCalories : 0,
      calories: item.values.calories,
      carbsAllocation: macroCalories > 0 ? item.values.carbs_g * 4 * 100 / macroCalories : 0,
      carbsGrams: item.values.carbs_g,
      fatAllocation: macroCalories > 0 ? item.values.fat_g * 9 * 100 / macroCalories : 0,
      fatGrams: item.values.fat_g,
      id: `${item.position}-${item.id}`,
      name: item.quantity == null ? item.name : `${item.name} (${item.quantity.toLocaleString("es-CL", { maximumFractionDigits: 1 })}g)`,
      proteinAllocation: macroCalories > 0 ? item.values.protein_g * 4 * 100 / macroCalories : 0,
      proteinGrams: item.values.protein_g,
      proteinPerKilogram: item.values.protein_per_kilogram,
      quantity: item.quantity ?? 1,
      quantityUnit: item.quantity == null ? "unidad" : "g",
    };
  });
}

export function SavedComparisonPreviewPanels({ items, scope }: { items?: ComparisonResultItem[]; scope: ComparisonScope }) {
  const [activeTab, setActiveTab] = useState<ComparisonPreviewTab>("calories");
  const panelItems = comparisonPanelItems(items ?? []);
  const leadingLabel = scopeLabels[scope];
  const tabs = [
    { key: "calories" as const, label: "Calorías" },
    { key: "macros" as const, label: "Macros" },
    { key: "distribution" as const, label: "Dist" },
    { key: "allocation" as const, label: "Alloc" },
  ];
  if (panelItems.length === 0) return null;
  return (
    <PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={tabs} />
      {activeTab === "calories" ? <NutritionCaloriesPanel items={panelItems} leadingLabel={leadingLabel} /> : null}
      {activeTab === "macros" ? <NutritionMacrosPanel items={panelItems} leadingLabel={leadingLabel} /> : null}
      {activeTab === "distribution" ? <NutritionDistributionPanel items={panelItems} leadingLabel={leadingLabel} /> : null}
      {activeTab === "allocation" ? <NutritionAllocationPanel items={panelItems} leadingLabel={leadingLabel} /> : null}
    </PanelSurface>
  );
}

export function ComparisonSelectionCard({
  entity,
  index,
  label,
  onRemove,
  quantity,
}: {
  entity: ComparisonScope;
  index: number;
  label?: string;
  onRemove?: () => void;
  quantity?: string;
}) {
  return (
    <View style={[styles.selectionCard, entityBorderStyle(entity)]}>
      <View style={styles.selectionHeading}>
        <View style={styles.selectionIdentity}>
          <View style={styles.selectionCopy}>
            <Text style={styles.selectionEyebrow}>{scopeSingularLabels[entity]} {index}</Text>
            <View style={styles.selectionNameRow}>
              <EntityIcon entity={entity} size="compact" />
              <Text numberOfLines={1} style={styles.selectionName}>
                {label ?? `Seleccionar ${scopeSingularLabels[entity].toLowerCase()}`}
                {label && quantity ? <Text style={styles.metricSuffix}> {formatComparisonQuantity(quantity)}</Text> : null}
              </Text>
            </View>
          </View>
        </View>
        {onRemove ? (
          <Pressable accessibilityLabel={`Quitar ${label ?? "selección"}`} accessibilityRole="button" hitSlop={8} onPress={onRemove} style={({ pressed }) => [styles.removeButton, pressed && styles.pressed]}>
            <Trash2 color={tokens.color.textMuted} size={15} />
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

export function ComparisonEditorCard({
  entity,
  index,
  label,
  onOpenSelector,
  onQuantityChange,
  onRemove,
  quantity,
}: {
  entity: ComparisonScope;
  index: number;
  label?: string;
  onOpenSelector?: () => void;
  onQuantityChange?: (value: string) => void;
  onRemove?: () => void;
  quantity?: string;
}) {
  const singularLabel = scopeSingularLabels[entity];
  const supportsQuantity = entity !== "dailyPlan";

  return (
    <View style={[styles.editorCard, entityBorderStyle(entity)]}>
      <View style={styles.editorField}>
        <Text style={styles.editorFieldLabel}>{singularLabel} {index}</Text>
        <View style={styles.editorSelectRow}>
          <Pressable accessibilityLabel={`Seleccionar ${singularLabel.toLowerCase()}`} accessibilityRole="button" onPress={onOpenSelector} style={({ pressed }) => [styles.editorSelect, pressed && styles.pressed]}>
            {label ? <EntityIcon entity={entity} size="compact" /> : null}
            <Text numberOfLines={1} style={[styles.editorInputText, !label && styles.editorPlaceholder]}>{label ?? `Seleccionar ${singularLabel.toLowerCase()}`}</Text>
            <ChevronDown color={tokens.color.textMuted} size={16} />
          </Pressable>
          {label && onRemove ? (
            <Pressable accessibilityLabel={`Quitar ${label}`} accessibilityRole="button" hitSlop={8} onPress={onRemove} style={({ pressed }) => [styles.removeButton, pressed && styles.pressed]}>
              <Trash2 color={tokens.color.textMuted} size={15} />
            </Pressable>
          ) : null}
        </View>
      </View>

      {supportsQuantity && label ? (
        <View style={[styles.editorField, styles.quantityField]}>
          <Text style={styles.editorFieldLabel}>Cantidad</Text>
          <View style={styles.quantityInputWrap}>
            <TextInput
              accessibilityLabel="Cantidad en gramos"
              inputMode="numeric"
              onChangeText={onQuantityChange}
              style={styles.quantityInput}
              value={quantity}
            />
            <Text style={styles.quantityUnit}>g</Text>
          </View>
        </View>
      ) : null}
    </View>
  );
}

export function ComparisonBuilder({ addActionLabel, children, onAdd, onCompare, onSave, scope }: { addActionLabel?: string; children: React.ReactNode; onAdd?: () => void; onCompare?: () => void; onSave?: () => void; scope: ComparisonScope }) {
  const resolvedAddActionLabel = addActionLabel ?? `Agregar ${scopeSingularLabels[scope].toLowerCase()}`;
  return (
    <View style={[styles.builder, entityBorderStyle(scope)]}>
      <View style={styles.builderEyebrow}>
        <SectionIcon section="comparator" size="compact" />
        <Text style={styles.builderEyebrowText}>Nueva comparación</Text>
      </View>
      <View style={styles.builderSelections}>{children}</View>
      <View style={styles.builderActions}>
        {onAdd ? <Button label={resolvedAddActionLabel} onPress={onAdd} variant="secondary" /> : null}
        {onSave ? <Button label="Guardar comparación" onPress={onSave} variant="secondary" /> : null}
        {onCompare ? <Button label="Comparar" onPress={onCompare} /> : null}
      </View>
    </View>
  );
}

export type ComparisonBarItem = {
  entity: ComparisonScope;
  formattedValue: string;
  id: string;
  label: string;
  labelSuffix?: string;
  width: number;
};

export function ComparisonMetricCard({ barVariant = "continuous", items, label, tone, unit }: { barVariant?: "compactAlloc" | "continuous"; items: ComparisonBarItem[]; label: string; tone: ComparisonMetricTone; unit: string }) {
  const color = metricColors[tone];
  const entity = items[0]?.entity;
  return (
    <View style={[styles.metricCard, entity ? entityBorderStyle(entity) : null]}>
      <View style={styles.metricHeader}>
        <Text style={styles.metricTitle}>{label}</Text>
        <Text style={styles.metricUnit}>{unit}</Text>
      </View>
      <View style={styles.metricBars}>
        {items.map((item) => {
          const width = Math.max(0, Math.min(item.width, 100));
          return (
            <View key={item.id} style={styles.metricRow}>
              <View style={styles.metricMeta}>
                <EntityIcon entity={item.entity} size="compact" />
                <Text numberOfLines={1} style={styles.metricLabel}>{item.label}{item.labelSuffix ? <Text style={styles.metricSuffix}> {item.labelSuffix}</Text> : null}</Text>
                <Text style={styles.metricValue}>{item.formattedValue}</Text>
              </View>
              {barVariant === "compactAlloc" ? (
                <PanelAllocationBar accessibilityLabel={`${item.label}: ${item.formattedValue}`} showValue={false} size="compact" tone={tone} value={width} />
              ) : (
                <View accessibilityLabel={`${item.label}: ${item.formattedValue}`} accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: width }} style={styles.metricTrack}>
                  <View style={[styles.metricFill, { backgroundColor: color, width: `${width}%` }]} />
                </View>
              )}
            </View>
          );
        })}
      </View>
    </View>
  );
}

export function SavedComparisonCard({ items, scope = "food", title }: { items: FoodPanelItem[]; scope?: ComparisonScope; title: string }) {
  return (
    <View style={[styles.savedCard, entityBorderStyle(scope)]}>
      <View style={styles.savedCardHeading}>
        <View style={styles.builderEyebrow}>
          <SectionIcon section="comparator" size="compact" />
          <Text style={styles.builderEyebrowText}>Comparación guardada</Text>
        </View>
        <Text style={styles.savedTitle}>{title}</Text>
        <StructuralIndicators indicators={[{ icon: "food", label: "alimentos", value: items.length }]} />
      </View>
      <View style={styles.savedCardPanel}>
        <FoodPanels items={items} />
      </View>
    </View>
  );
}

export function SavedComparisonDetailPage({
  children,
  itemCount,
  onEdit,
  scope,
  selections,
  title,
}: PropsWithChildren<{
  itemCount: number;
  onEdit?: () => void;
  scope: ComparisonScope;
  selections: ReactNode;
  title: string;
}>) {
  const { width } = useWindowDimensions();
  const titleSize = width < 420 ? 22 : 24;
  const titleLineHeight = width < 420 ? 32 : 34;

  return (
    <View style={[styles.savedDetailPage, entityBorderStyle(scope)]}>
      <View style={styles.savedDetailHero}>
        <View style={styles.builderEyebrow}>
          <SectionIcon section="comparator" size="compact" />
          <Text style={styles.builderEyebrowText}>Comparación guardada</Text>
        </View>
        <Text style={[styles.savedDetailTitle, { fontSize: titleSize, lineHeight: titleLineHeight }]}>{title}</Text>
        <StructuralIndicators indicators={[{ icon: scope, label: scopeLabels[scope].toLowerCase(), value: itemCount }]} />
      </View>

      <View style={styles.savedDetailSection}>
        <SectionHeading title="Elementos comparados" />
        <View style={styles.savedDetailSelections}>{selections}</View>
      </View>

      <View style={styles.savedDetailSection}>
        <SectionHeading title="Resultados comparativos" />
        <View style={styles.savedDetailResults}>{children}</View>
      </View>

      {onEdit ? <Button label="Editar comparación" onPress={onEdit} variant="secondary" /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.7 },
  selectionCard: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.spacing.md },
  selectionHeading: { alignItems: "flex-start", flexDirection: "row", justifyContent: "space-between", minWidth: 0 },
  selectionIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  selectionCopy: { flex: 1, gap: tokens.spacing.xs, minWidth: 0 },
  selectionEyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight },
  selectionNameRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  selectionName: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  removeButton: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, height: 32, justifyContent: "center", width: 32 },
  builder: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.md, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.card.outerPadding },
  builderEyebrow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  builderEyebrowText: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 0, textTransform: "uppercase" },
  builderSelections: { gap: tokens.spacing.sm },
  editorCard: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, gap: tokens.spacing.md, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.spacing.md },
  editorField: { gap: tokens.spacing.compact },
  editorFieldLabel: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold },
  editorSelectRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  editorSelect: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 40, minWidth: 0, paddingHorizontal: tokens.spacing.sm },
  editorInputText: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular },
  editorPlaceholder: { color: tokens.color.textMuted },
  quantityField: { maxWidth: 150 },
  quantityInputWrap: { justifyContent: "center" },
  quantityInput: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, color: tokens.color.textMain, fontSize: tokens.type.caption, minHeight: 40, paddingHorizontal: tokens.spacing.sm, paddingRight: 34 },
  quantityUnit: { color: tokens.color.textSoft, fontSize: tokens.type.label, position: "absolute", right: tokens.spacing.sm },
  builderActions: { gap: tokens.spacing.sm },
  metricCard: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.md, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.card.outerPadding },
  metricHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  metricTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  metricUnit: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  metricBars: { gap: tokens.spacing.md },
  metricRow: { gap: tokens.spacing.compact },
  metricMeta: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  metricLabel: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  metricSuffix: { color: tokens.color.textMuted, fontWeight: tokens.weight.regular },
  metricValue: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold },
  metricTrack: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, height: 11, overflow: "hidden" },
  metricFill: { borderRadius: tokens.radius.pill, height: "100%" },
  savedCard: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.card.gap, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minWidth: 0, padding: tokens.card.outerPadding },
  savedCardHeading: { gap: tokens.spacing.xs, minWidth: 0 },
  savedTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.semibold, lineHeight: 25 },
  savedCardPanel: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minWidth: 0 },
  savedDetailPage: { alignSelf: "stretch", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.lg, marginHorizontal: -tokens.spacing.screen, minWidth: 0, padding: tokens.card.outerPadding },
  savedDetailHero: { gap: tokens.spacing.compact, minWidth: 0 },
  savedDetailTitle: { color: tokens.color.textMain, fontWeight: tokens.weight.semibold, letterSpacing: 0 },
  savedDetailSection: { gap: tokens.spacing.sm, minWidth: 0 },
  savedDetailSelections: { gap: tokens.spacing.sm },
  savedDetailResults: { gap: tokens.spacing.sm },
});
