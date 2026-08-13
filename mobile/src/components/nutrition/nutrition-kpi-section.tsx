import { StyleProp, StyleSheet, Text, useWindowDimensions, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";

import { AllocationTone, KpiAllocationBar } from "./allocation-bar";
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
  style?: StyleProp<ViewStyle>;
};

type MacroRowProps = MacroKpi & {
  label: string;
  tone: AllocationTone;
  density: "compact" | "regular";
  fontSize: 12 | 13;
  isLast?: boolean;
  refined: boolean;
  perKilogram?: number | null;
};

function rounded(value: number): number {
  return Number.isFinite(value) ? Math.round(value) : 0;
}

function MacroRow({ label, tone, grams, allocation, perKilogram, density, fontSize, isLast = false, refined }: MacroRowProps) {
  const compact = density === "compact";
  return (
    <View style={[styles.macroRow, refined && styles.macroRowSlightlyTight, compact && styles.macroRowCompact, isLast && styles.macroRowLast]}>
      <Text style={[styles.macroLabel, compact && styles.macroLabelCompact, { fontSize }]}>{label}</Text>
      <View style={[styles.ppkSlot, compact && styles.ppkSlotCompact]}>
        {perKilogram != null ? (
          <ProteinPerKilogramBadge density={density} textSize={fontSize} value={perKilogram} />
        ) : null}
      </View>
      <Text style={[styles.grams, compact && styles.gramsCompact, { fontSize }]}>{rounded(grams)} g</Text>
      <KpiAllocationBar
        accessibilityLabel={`${label}: ${rounded(grams)} gramos, ${rounded(allocation)}% de distribucion`}
        size={density}
        style={[styles.allocationBar, refined && styles.allocationBarSlightlyTight]}
        textSize={fontSize}
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
  const { width } = useWindowDimensions();
  const compact = density === "compact";
  const refined = !compact && width < 420;
  const macroFontSize = width < 420 ? 12 : 13;
  return (
    <View style={[styles.container, compact && styles.containerCompact, style]}>
      <View
        accessibilityLabel={`${rounded(calories)} calorias`}
        accessible
        style={[
          styles.calories,
          compact && styles.caloriesCompact,
        ]}>
        <Text
          style={[
            styles.caloriesLabel,
            compact && styles.caloriesLabelCompact,
            !compact && styles.caloriesLabelRegular,
          ]}>
          Calorias
        </Text>
        <CalorieValue compact value={rounded(calories)} />
        <Text style={[styles.caloriesUnit, compact && styles.caloriesLabelCompact]}>kcal</Text>
      </View>
      <View style={styles.macros}>
        <MacroRow density={density} fontSize={macroFontSize} label="Proteina" refined={refined} tone="protein" {...protein} />
        <MacroRow density={density} fontSize={macroFontSize} label="Carbos" refined={refined} tone="carbs" {...carbs} />
        <MacroRow density={density} fontSize={macroFontSize} isLast label="Grasas" refined={refined} tone="fat" {...fat} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "stretch", flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0, width: "100%" },
  containerCompact: { gap: tokens.spacing.compact },
  calories: { alignItems: "center", alignSelf: "center", aspectRatio: 1, backgroundColor: tokens.color.kcalSurface, borderColor: tokens.color.kcalBorder, borderRadius: tokens.radius.card, borderWidth: 3, flexShrink: 0, justifyContent: "center", minHeight: 102, paddingHorizontal: 5, width: 102 },
  caloriesCompact: { borderRadius: tokens.radius.lg, borderWidth: 2, minHeight: 82, width: 82 },
  caloriesLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "500", letterSpacing: 0 },
  caloriesLabelCompact: { fontSize: tokens.type.label },
  caloriesLabelRegular: { fontSize: 10 },
  caloriesUnit: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "500", letterSpacing: 0 },
  macros: { flex: 1, minWidth: 0 },
  macroRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.xs, minWidth: 0, paddingVertical: 5 },
  macroRowSlightlyTight: { paddingVertical: tokens.spacing.xs },
  macroRowCompact: { gap: 3, paddingVertical: 4 },
  macroRowLast: { borderBottomWidth: 0 },
  macroLabel: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: "500", letterSpacing: 0, width: 52 },
  macroLabelCompact: { width: 52 },
  ppkSlot: { alignItems: "stretch", justifyContent: "center", width: 60 },
  ppkSlotCompact: { width: 60 },
  grams: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: "500", fontVariant: ["tabular-nums"], letterSpacing: 0, textAlign: "right", width: 40 },
  gramsCompact: { width: 40 },
  allocationBar: { flex: 1, minWidth: 0, width: "auto" },
  allocationBarSlightlyTight: { height: 22 },
});
