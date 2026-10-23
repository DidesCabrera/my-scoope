import { ChevronDown, Scale } from "lucide-react-native";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { tokens } from "@/design/tokens";
import { convertFoodPortionAmount, type FoodPortionMeasure } from "./food-portion-nutrition";
import type { FoodPortionFieldProps } from "./food-portion-field.types";

function displayNumber(value: number): string {
  return value.toLocaleString("es-CL", { maximumFractionDigits: 2 });
}

export function FoodPortionField({ equivalentMetricAmount, householdDefaultAmount, householdDetail, householdMeasureLabel, label, measure, metricDefaultAmount, metricUnit, onChange, onMeasureChange, value }: FoodPortionFieldProps) {
  const householdAvailable = Boolean(householdMeasureLabel && householdDefaultAmount && householdDefaultAmount > 0 && metricDefaultAmount && metricDefaultAmount > 0);
  const measureLabel = measure === "household" && householdAvailable ? householdMeasureLabel : metricUnit;
  const changeMeasure = () => {
    if (!householdAvailable) return;
    const next: FoodPortionMeasure = measure === "household" ? "metric" : "household";
    const converted = convertFoodPortionAmount(value, measure, next, {
      defaultPortion: metricDefaultAmount,
      householdAmount: householdDefaultAmount,
      householdMeasure: householdMeasureLabel,
      householdMeasureLabel,
    });
    onMeasureChange(next);
    onChange(converted);
  };
  return (
    <View style={styles.field}>
      <View style={styles.row}>
        <View style={styles.labelRow}><Scale color={tokens.color.textMain} size={18} /><Text style={styles.label}>{label}</Text></View>
        <View style={styles.selectors}>
          <TextInput accessibilityLabel="Cantidad" inputMode="decimal" onChangeText={onChange} style={[styles.selector, styles.amount]} value={value} />
          <Pressable accessibilityLabel={`Medida: ${measureLabel}`} accessibilityRole="button" disabled={!householdAvailable} onPress={changeMeasure} style={({ pressed }) => [styles.selector, styles.measure, pressed && styles.pressed]}>
            <Text numberOfLines={1} style={styles.selectorText}>{measureLabel}</Text><ChevronDown color={tokens.color.textSoft} size={16} />
          </Pressable>
        </View>
      </View>
      {measure === "household" && equivalentMetricAmount > 0 ? <Text style={styles.equivalence}>Equivale a {displayNumber(equivalentMetricAmount)} {metricUnit}{householdDetail ? ` · ${householdDetail}` : ""}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  amount: { minWidth: 68, textAlign: "center" },
  equivalence: { color: tokens.color.textMuted, fontSize: tokens.type.caption, marginLeft: 26, marginTop: 6 },
  field: { gap: 7 },
  label: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  labelRow: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  measure: { alignItems: "center", flexDirection: "row", gap: 2, justifyContent: "center", maxWidth: 128, minWidth: 82 },
  pressed: { opacity: 0.72 },
  row: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  selector: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, color: tokens.color.textMain, fontSize: 16, minHeight: 36, paddingHorizontal: 8 },
  selectorText: { color: tokens.color.textMain, flexShrink: 1, fontSize: 16 },
  selectors: { alignItems: "center", flexDirection: "row", gap: 6, marginLeft: 8 },
});
