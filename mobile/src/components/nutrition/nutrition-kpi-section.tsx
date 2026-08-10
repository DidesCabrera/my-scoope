import { StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";
import { AllocationTone, KpiAllocationBar } from "./allocation-bar";
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
  style?: StyleProp<ViewStyle>;
};

type MacroRowProps = MacroKpi & {
  label: string;
  tone: AllocationTone;
  density: "compact" | "regular";
  perKilogram?: number | null;
};

function rounded(value: number): number {
  return Number.isFinite(value) ? Math.round(value) : 0;
}

function MacroRow({ label, tone, grams, allocation, perKilogram, density }: MacroRowProps) {
  const compact = density === "compact";
  return (
    <View style={[styles.macroRow, compact && styles.macroRowCompact]}>
      <Text style={[styles.macroLabel, compact && styles.macroLabelCompact]}>{label}</Text>
      <View style={[styles.ppkSlot, compact && styles.ppkSlotCompact]}>
        {perKilogram != null ? (
          <ProteinPerKilogramBadge density={density} value={perKilogram} />
        ) : null}
      </View>
      <Text style={[styles.grams, compact && styles.gramsCompact]}>{rounded(grams)} g</Text>
      <KpiAllocationBar
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
        <Text style={[styles.caloriesValue, compact && styles.caloriesValueCompact]}>{rounded(calories)}</Text>
        <Text style={[styles.caloriesUnit, compact && styles.caloriesLabelCompact]}>kcal</Text>
      </View>
      <View style={styles.macros}>
        <MacroRow density={density} label="Proteína" tone="protein" {...protein} />
        <MacroRow density={density} label="Carbos" tone="carbs" {...carbs} />
        <MacroRow density={density} label="Grasas" tone="fat" {...fat} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "stretch", flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0, width: "100%" },
  containerCompact: { gap: tokens.spacing.compact },
  calories: { alignItems: "center", alignSelf: "stretch", backgroundColor: tokens.color.kcalSurface, borderColor: tokens.color.kcalBorder, borderRadius: tokens.radius.card, borderWidth: 3, justifyContent: "center", paddingHorizontal: 5, width: 80 },
  caloriesCompact: { borderRadius: tokens.radius.lg, borderWidth: 2, width: 68 },
  caloriesLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium },
  caloriesLabelCompact: { fontSize: tokens.type.label },
  caloriesValue: { color: tokens.color.textMain, fontSize: 29, fontWeight: tokens.weight.bold, fontVariant: ["tabular-nums"] },
  caloriesValueCompact: { fontSize: 23 },
  caloriesUnit: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.medium },
  macros: { flex: 1, minWidth: 0 },
  macroRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.xs, minWidth: 0, paddingVertical: 5 },
  macroRowCompact: { gap: 3, paddingVertical: 4 },
  macroLabel: { color: tokens.color.textMain, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold, width: 52 },
  macroLabelCompact: { fontSize: 11, width: 48 },
  ppkSlot: { alignItems: "stretch", justifyContent: "center", width: 60 },
  ppkSlotCompact: { width: 52 },
  grams: { color: tokens.color.textMain, fontSize: tokens.type.label, fontWeight: tokens.weight.medium, fontVariant: ["tabular-nums"], textAlign: "right", width: 40 },
  gramsCompact: { fontSize: 11, width: 34 },
  allocationBar: { flex: 1, minWidth: 0, width: "auto" },
});
