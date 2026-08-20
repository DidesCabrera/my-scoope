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
  variant?: "nested" | "regular";
  style?: StyleProp<ViewStyle>;
};

type MacroRowProps = MacroKpi & {
  label: string;
  tone: AllocationTone;
  variant: "nested" | "regular";
  fontSize: 12 | 13;
  isLast?: boolean;
  refined: boolean;
  perKilogram?: number | null;
};

function rounded(value: number): number {
  return Number.isFinite(value) ? Math.round(value) : 0;
}

function MacroRow({ label, tone, grams, allocation, perKilogram, variant, fontSize, isLast = false, refined }: MacroRowProps) {
  const nested = variant === "nested";
  const density = nested ? "compact" : "regular";
  return (
    <View style={[styles.macroRow, refined && styles.macroRowSlightlyTight, nested && styles.macroRowCompact, isLast && styles.macroRowLast]}>
      <Text style={[styles.macroLabel, nested && styles.macroLabelCompact, { fontSize }]}>{label}</Text>
      <View style={[styles.ppkSlot, nested && styles.ppkSlotCompact]}>
        {perKilogram != null ? (
          <ProteinPerKilogramBadge density={density} textSize={fontSize} value={perKilogram} />
        ) : null}
      </View>
      <Text style={[styles.grams, nested && styles.gramsCompact, { fontSize }]}>{rounded(grams)} g</Text>
      <KpiAllocationBar
        accessibilityLabel={`${label}: ${rounded(grams)} gramos, ${rounded(allocation)}% de distribución`}
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
  variant = "regular",
  style,
}: NutritionKpiSectionProps) {
  const { width } = useWindowDimensions();
  const nested = variant === "nested";
  const refined = !nested && width < 420;
  const macroFontSize = width < 420 ? 12 : 13;
  return (
    <View style={[styles.container, nested && styles.containerNested, style]}>
      <View
        accessibilityLabel={`${rounded(calories)} calorías`}
        accessible
        style={[styles.calories, nested && styles.caloriesNested]}>
        <Text
          style={[
            styles.caloriesLabel,
            nested && styles.caloriesLabelNested,
            !nested && styles.caloriesLabelRegular,
          ]}>
          Calorías
        </Text>
        <CalorieValue compact={nested} value={rounded(calories)} />
        <Text style={[styles.caloriesUnit, nested && styles.caloriesLabelNested]}>kcal</Text>
      </View>
      <View style={styles.macros}>
        <MacroRow fontSize={macroFontSize} label="Proteína" refined={refined} tone="protein" variant={variant} {...protein} />
        <MacroRow fontSize={macroFontSize} label="Carbos" refined={refined} tone="carbs" variant={variant} {...carbs} />
        <MacroRow fontSize={macroFontSize} isLast label="Grasas" refined={refined} tone="fat" variant={variant} {...fat} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "stretch", flexDirection: "row", gap: tokens.component.nutritionKpi.regular.contentGap, minWidth: 0, width: "100%" },
  containerNested: { gap: tokens.component.nutritionKpi.nested.contentGap },
  calories: { alignItems: "center", alignSelf: "center", backgroundColor: tokens.color.kcalSurface, borderColor: tokens.color.kcalBorder, borderRadius: tokens.component.nutritionKpi.regular.totalRadius, borderWidth: tokens.component.nutritionKpi.regular.totalBorderWidth, flexShrink: 0, height: tokens.component.nutritionKpi.regular.totalSize, justifyContent: "center", paddingHorizontal: 5, width: tokens.component.nutritionKpi.regular.totalSize },
  caloriesNested: { borderRadius: tokens.component.nutritionKpi.nested.totalRadius, borderWidth: tokens.component.nutritionKpi.nested.totalBorderWidth, height: tokens.component.nutritionKpi.nested.totalSize, width: tokens.component.nutritionKpi.nested.totalSize },
  caloriesLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, letterSpacing: 0 },
  caloriesLabelNested: { fontSize: tokens.type.label },
  caloriesLabelRegular: { fontSize: 10 },
  caloriesUnit: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.medium, letterSpacing: 0 },
  macros: { flex: 1, minWidth: 0 },
  macroRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.xs, minWidth: 0, paddingVertical: 5 },
  macroRowSlightlyTight: { paddingVertical: tokens.spacing.xs },
  macroRowCompact: { gap: 3, paddingVertical: 4 },
  macroRowLast: { borderBottomWidth: 0 },
  macroLabel: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, letterSpacing: 0, width: 52 },
  macroLabelCompact: { width: 52 },
  ppkSlot: { alignItems: "stretch", justifyContent: "center", width: 60 },
  ppkSlotCompact: { width: 60 },
  grams: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, fontVariant: ["tabular-nums"], letterSpacing: 0, textAlign: "right", width: 40 },
  gramsCompact: { width: 40 },
  allocationBar: { flex: 1, minWidth: 0, width: "auto" },
  allocationBarSlightlyTight: { height: tokens.component.nutritionKpi.regular.narrowBarHeight },
});
