import { StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";
import { AllocationTone, KpiAllocationBar } from "./allocation-bar";
import { CalorieValue } from "./calorie-value";
import { ProteinPerKilogramBadge } from "./protein-per-kilogram-badge";

type MacroKpi = {
  grams: number;
  allocation: number;
};

export type CalorieSurfaceScale = 0.8 | 0.85 | 0.9 | 1;

export type NutritionKpiSectionProps = {
  calories: number;
  protein: MacroKpi & { perKilogram?: number | null };
  carbs: MacroKpi;
  fat: MacroKpi;
  density?: "compact" | "regular";
  calorieSurfaceScale?: CalorieSurfaceScale;
  style?: StyleProp<ViewStyle>;
};

const calorieSurfaceHeights: Record<CalorieSurfaceScale, `${number}%`> = {
  0.8: "80%",
  0.85: "85%",
  0.9: "90%",
  1: "100%",
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
  calorieSurfaceScale = 1,
  style,
}: NutritionKpiSectionProps) {
  const compact = density === "compact";
  return (
    <View style={[styles.container, compact && styles.containerCompact, style]}>
      <View
        accessibilityLabel={`${rounded(calories)} calorías`}
        accessible
        style={[
          styles.calories,
          compact && styles.caloriesCompact,
          { height: calorieSurfaceHeights[calorieSurfaceScale] },
        ]}>
        <Text style={[styles.caloriesLabel, compact && styles.caloriesLabelCompact]}>Calorías</Text>
        <CalorieValue compact value={rounded(calories)} />
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
  calories: { alignItems: "center", alignSelf: "center", aspectRatio: 1, backgroundColor: tokens.color.kcalSurface, borderColor: tokens.color.kcalBorder, borderRadius: tokens.radius.card, borderWidth: 3, flexShrink: 0, justifyContent: "center", paddingHorizontal: 5 },
  caloriesCompact: { borderRadius: tokens.radius.lg, borderWidth: 2 },
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
