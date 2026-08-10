import { StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";
import { AllocationTone, KpiAllocationBar, PanelAllocationBar } from "./allocation-bar";
import { CalorieValue } from "./calorie-value";
import { ProteinPerKilogramBadge } from "./protein-per-kilogram-badge";

type MacroKpi = {
  grams: number;
  allocation: number;
};

export type NutritionKpiSectionProps = {
  calories: number;
  protein: MacroKpi & { perKilogram?: number | null };
  carbs: MacroKpi;
  fat: MacroKpi;
  density?: "compact" | "regular";
  allocationVariant?: "kpi" | "panel";
  style?: StyleProp<ViewStyle>;
};

type MacroRowProps = MacroKpi & {
  label: string;
  tone: AllocationTone;
  density: "compact" | "regular";
  allocationVariant: "kpi" | "panel";
  perKilogram?: number | null;
};

function rounded(value: number): number {
  return Number.isFinite(value) ? Math.round(value) : 0;
}

function MacroRow({ label, tone, grams, allocation, perKilogram, density, allocationVariant }: MacroRowProps) {
  const compact = density === "compact";
  const AllocationBar = allocationVariant === "panel" ? PanelAllocationBar : KpiAllocationBar;
  return (
    <View style={[styles.macroRow, compact && styles.macroRowCompact]}>
      <Text style={[styles.macroLabel, compact && styles.macroLabelCompact]}>{label}</Text>
      <View style={[styles.ppkSlot, compact && styles.ppkSlotCompact]}>
        {perKilogram != null ? (
          <ProteinPerKilogramBadge density={density} value={perKilogram} />
        ) : null}
      </View>
      <Text style={[styles.grams, compact && styles.gramsCompact]}>{rounded(grams)} g</Text>
      <AllocationBar
        accessibilityLabel={`${label}: ${rounded(grams)} gramos, ${rounded(allocation)}% de distribución`}
        size={density}
        style={styles.allocationBar}
        tone={tone}
        value={allocation}
      />
    </View>
  );
}

export function NutritionKpiSection({
  calories,
  protein,
  carbs,
  fat,
  density = "regular",
  allocationVariant = "kpi",
  style,
}: NutritionKpiSectionProps) {
  const compact = density === "compact";
  return (
    <View style={[styles.container, compact && styles.containerCompact, style]}>
      <View
        accessibilityLabel={`${rounded(calories)} calorías`}
        accessible
        style={[styles.calories, compact && styles.caloriesCompact]}>
        <Text style={[styles.caloriesLabel, compact && styles.caloriesLabelCompact]}>Calorías</Text>
        <CalorieValue compact={compact} value={rounded(calories)} />
        <Text style={[styles.caloriesUnit, compact && styles.caloriesLabelCompact]}>kcal</Text>
      </View>
      <View style={styles.macros}>
        <MacroRow allocationVariant={allocationVariant} density={density} label="Proteína" tone="protein" {...protein} />
        <MacroRow allocationVariant={allocationVariant} density={density} label="Carbos" tone="carbs" {...carbs} />
        <MacroRow allocationVariant={allocationVariant} density={density} label="Grasas" tone="fat" {...fat} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "stretch", flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0, width: "100%" },
  containerCompact: { gap: tokens.spacing.compact },
  calories: { alignItems: "center", alignSelf: "stretch", backgroundColor: tokens.color.kcalSurface, borderColor: tokens.color.kcalBorder, borderRadius: tokens.radius.card, borderWidth: 3, justifyContent: "center", paddingHorizontal: 5, width: 80 },
  caloriesCompact: { borderRadius: tokens.radius.lg, borderWidth: 2, width: 68 },
  caloriesLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, letterSpacing: 0 },
  caloriesLabelCompact: { fontSize: tokens.type.label },
  caloriesUnit: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.medium, letterSpacing: 0 },
  macros: { flex: 1, minWidth: 0 },
  macroRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.xs, minWidth: 0, paddingVertical: 5 },
  macroRowCompact: { gap: 3, paddingVertical: 4 },
  macroLabel: { color: tokens.color.textMain, fontSize: tokens.type.label, fontWeight: tokens.weight.regular, letterSpacing: 0, width: 52 },
  macroLabelCompact: { fontSize: 11, width: 48 },
  ppkSlot: { alignItems: "stretch", justifyContent: "center", width: 60 },
  ppkSlotCompact: { width: 52 },
  grams: { color: tokens.color.textMain, fontSize: tokens.type.label, fontWeight: tokens.weight.medium, fontVariant: ["tabular-nums"], letterSpacing: 0, textAlign: "right", width: 40 },
  gramsCompact: { fontSize: 11, width: 34 },
  allocationBar: { flex: 1, minWidth: 0, width: "auto" },
});
