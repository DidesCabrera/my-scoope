import { Picker } from "@react-native-picker/picker";
import { Check, ChevronDown, Scale } from "lucide-react-native";
import { useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";

import { PORTION_VALUES } from "@/components/ui/native-measurement-values";
import { nativeWheelMetrics } from "@/components/ui/native-wheel-metrics";
import { tokens } from "@/design/tokens";
import { convertFoodPortionAmount, type FoodPortionMeasure } from "./food-portion-nutrition";
import type { FoodPortionFieldProps } from "./food-portion-field.types";

const HOUSEHOLD_PORTION_VALUES = Array.from({ length: 80 }, (_, index) => (index + 1) / 4);

function numericValue(value: string, fallback: number): number {
  const parsed = Number(value.trim().replace(",", "."));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function displayNumber(value: number): string {
  return value.toLocaleString("es-CL", { maximumFractionDigits: 2 });
}

export function FoodPortionField({
  equivalentMetricAmount,
  householdDefaultAmount,
  householdDetail,
  householdMeasureLabel,
  label,
  measure,
  metricDefaultAmount,
  metricUnit,
  onChange,
  onMeasureChange,
  value,
}: FoodPortionFieldProps) {
  const householdAvailable = Boolean(householdMeasureLabel && householdDefaultAmount && householdDefaultAmount > 0 && metricDefaultAmount && metricDefaultAmount > 0);
  const [visible, setVisible] = useState(false);
  const [draftMeasure, setDraftMeasure] = useState<FoodPortionMeasure>(measure);
  const [draftAmount, setDraftAmount] = useState(() => numericValue(value, measure === "household" ? householdDefaultAmount ?? 1 : metricDefaultAmount ?? 100));
  const pickerStyle = Platform.OS === "ios" ? styles.iosPicker : styles.androidPicker;

  const open = () => {
    setDraftMeasure(measure);
    setDraftAmount(numericValue(value, measure === "household" ? householdDefaultAmount ?? 1 : metricDefaultAmount ?? 100));
    setVisible(true);
  };

  const changeMeasure = (next: FoodPortionMeasure) => {
    const converted = convertFoodPortionAmount(String(draftAmount), draftMeasure, next, {
      defaultPortion: metricDefaultAmount,
      householdAmount: householdDefaultAmount,
      householdMeasure: householdMeasureLabel,
      householdMeasureLabel,
    });
    setDraftMeasure(next);
    setDraftAmount(numericValue(converted, draftAmount));
  };

  const commit = () => {
    onMeasureChange(draftMeasure);
    onChange(String(draftAmount));
    setVisible(false);
  };

  const measureLabel = measure === "household" && householdAvailable ? householdMeasureLabel : metricUnit;
  const equivalence = measure === "household" && equivalentMetricAmount > 0
    ? `Equivale a ${displayNumber(equivalentMetricAmount)} ${metricUnit}${householdDetail ? ` · ${householdDetail}` : ""}`
    : null;

  return (
    <View style={styles.field}>
      <View style={styles.row}>
        <View style={styles.labelRow}>
          <Scale color={tokens.color.textMain} size={18} />
          <Text style={styles.label}>{label}</Text>
        </View>
        <View style={styles.selectors}>
          <Pressable accessibilityLabel={`Cantidad: ${value}`} accessibilityRole="button" accessibilityState={{ expanded: visible }} onPress={open} style={({ pressed }) => [styles.selector, styles.amountSelector, pressed && styles.pressed]}>
            <Text numberOfLines={1} style={styles.selectorText}>{displayNumber(numericValue(value, 0))}</Text>
            <ChevronDown color={tokens.color.textSoft} size={16} />
          </Pressable>
          <Pressable accessibilityLabel={`Medida: ${measureLabel}`} accessibilityRole="button" accessibilityState={{ expanded: visible }} onPress={open} style={({ pressed }) => [styles.selector, styles.measureSelector, pressed && styles.pressed]}>
            <Text numberOfLines={1} style={styles.selectorText}>{measureLabel}</Text>
            <ChevronDown color={tokens.color.textSoft} size={16} />
          </Pressable>
        </View>
      </View>
      {equivalence ? <Text accessibilityLiveRegion="polite" style={styles.equivalence}>{equivalence}</Text> : null}
      {visible ? (
        <View style={styles.inlinePicker}>
          <View accessibilityLabel="Cantidad y medida de la porción" style={styles.pickers}>
            <View style={styles.amountPickerColumn}>
              <Picker dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => setDraftAmount(Number(next))} selectedValue={draftAmount} style={pickerStyle}>
                {[...new Set([...(draftMeasure === "household" ? HOUSEHOLD_PORTION_VALUES : PORTION_VALUES), draftAmount])].sort((a, b) => a - b).map((option) => <Picker.Item key={option} label={displayNumber(option)} value={option} />)}
              </Picker>
            </View>
            <View style={styles.measurePickerColumn}>
              <Picker dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => changeMeasure(next as FoodPortionMeasure)} selectedValue={draftMeasure} style={pickerStyle}>
                {householdAvailable ? <Picker.Item label={householdMeasureLabel} value="household" /> : null}
                <Picker.Item label={metricUnit} value="metric" />
              </Picker>
            </View>
          </View>
          <Pressable accessibilityLabel="Listo" accessibilityRole="button" onPress={commit} style={({ pressed }) => [styles.doneButton, pressed && styles.pressed]}>
            <Check color={tokens.color.interactivePrimary} size={22} strokeWidth={2.6} />
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  amountPickerColumn: { flex: 0, width: 112 },
  amountSelector: { minWidth: 68 },
  androidPicker: { color: tokens.color.textMain, minHeight: 54, width: "100%" },
  doneButton: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.pill, bottom: tokens.spacing.sm, height: 40, justifyContent: "center", position: "absolute", right: tokens.spacing.sm, width: 40, zIndex: 2 },
  equivalence: { color: tokens.color.textMuted, fontSize: tokens.type.caption, marginLeft: 26, marginTop: 6 },
  field: { gap: 7 },
  inlinePicker: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, overflow: "hidden", position: "relative" },
  iosPicker: { color: tokens.color.textMain, height: nativeWheelMetrics.height, width: "100%" },
  label: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  labelRow: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  measurePickerColumn: { flex: 0, width: 150 },
  measureSelector: { maxWidth: 128, minWidth: 82 },
  pickerItem: { color: tokens.color.textMain, fontSize: nativeWheelMetrics.fontSize },
  pickers: { alignItems: "center", flexDirection: "row", justifyContent: "center" },
  pressed: { opacity: 0.72 },
  row: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  selector: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, flexDirection: "row", gap: 2, justifyContent: "center", minHeight: 36, paddingHorizontal: 8 },
  selectorText: { color: tokens.color.textMain, flexShrink: 1, fontSize: 16, textAlign: "center" },
  selectors: { alignItems: "center", flexDirection: "row", gap: 6, marginLeft: 8 },
});
