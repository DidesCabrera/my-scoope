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
      <View style={styles.macroHeader}>
        <Text style={[styles.macroLabel, compact && styles.macroLabelCompact]}>{label}</Text>
        {perKilogram != null ? (
          <ProteinPerKilogramBadge density={density} value={perKilogram} />
        ) : <View style={styles.ppkSpacer} />}
        <Text style={[styles.grams, compact && styles.gramsCompact]}>{rounded(grams)} g</Text>
      </View>
      <KpiAllocationBar
        accessibilityLabel={`${label}: ${rounded(grams)} gramos, ${rounded(allocation)}% de distribución`}
        size={density}
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
        <MacroRow density={density} label="Carbohidratos" tone="carbs" {...carbs} />
        <MacroRow density={density} label="Grasas" tone="fat" {...fat} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "stretch", flexDirection: "row", gap: tokens.spacing.md, minWidth: 0, width: "100%" },
  containerCompact: { gap: tokens.spacing.sm },
  calories: { alignItems: "center", alignSelf: "stretch", backgroundColor: tokens.color.kcalSurface, borderColor: tokens.color.kcalBorder, borderRadius: tokens.radius.card, borderWidth: 3, justifyContent: "center", paddingHorizontal: tokens.spacing.sm, width: 94 },
  caloriesCompact: { borderRadius: tokens.radius.lg, borderWidth: 2, width: 76 },
  caloriesLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  caloriesLabelCompact: { fontSize: tokens.type.label },
  caloriesValue: { color: tokens.color.textMain, fontSize: 29, fontWeight: "800", fontVariant: ["tabular-nums"] },
  caloriesValueCompact: { fontSize: 23 },
  caloriesUnit: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "700" },
  macros: { flex: 1, minWidth: 0 },
  macroRow: { borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, gap: 5, paddingVertical: tokens.spacing.sm },
  macroRowCompact: { gap: 3, paddingVertical: 5 },
  macroHeader: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  macroLabel: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: "700" },
  macroLabelCompact: { fontSize: tokens.type.label },
  ppkSpacer: { minWidth: 0 },
  grams: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: "700", fontVariant: ["tabular-nums"], minWidth: 42, textAlign: "right" },
  gramsCompact: { fontSize: tokens.type.label, minWidth: 36 },
});
