import { Picker } from "@react-native-picker/picker";
import { Check, ChevronDown, Scale } from "lucide-react-native";
import { useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";

import { PORTION_VALUES } from "@/components/ui/native-measurement-values";
import { nativeWheelMetrics } from "@/components/ui/native-wheel-metrics";
import { tokens } from "@/design/tokens";
import { convertFoodPortionAmount, householdMeasureDisplayLabel, type FoodPortionMeasure } from "./food-portion-nutrition";
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
  initiallyExpanded = false,
  label,
  measure,
  metricDefaultAmount,
  metricUnit,
  onChange,
  onMeasureChange,
  value,
}: FoodPortionFieldProps) {
  const householdAvailable = Boolean(householdMeasureLabel && householdDefaultAmount && householdDefaultAmount > 0 && metricDefaultAmount && metricDefaultAmount > 0);
  const [visible, setVisible] = useState(initiallyExpanded);
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

  const selectedAmount = numericValue(value, 0);
  const measureLabel = measure === "household" && householdAvailable && householdMeasureLabel ? householdMeasureDisplayLabel(householdMeasureLabel, selectedAmount) : metricUnit;
  const selectorLabel = `${displayNumber(selectedAmount)} ${measureLabel}`;
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
        <Pressable accessibilityLabel={`Porción: ${selectorLabel}`} accessibilityRole="button" accessibilityState={{ expanded: visible }} onPress={open} style={({ pressed }) => [styles.selector, pressed && styles.pressed]}>
          <Text numberOfLines={1} style={styles.selectorText}>{selectorLabel}</Text>
          <ChevronDown color={tokens.color.textSoft} size={16} />
        </Pressable>
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
            <Check color={tokens.color.food} size={22} strokeWidth={2.6} />
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  amountPickerColumn: { flex: 0, width: 112 },
  androidPicker: { color: tokens.color.textMain, minHeight: 54, width: "100%" },
  doneButton: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.pill, bottom: tokens.spacing.sm, height: 40, justifyContent: "center", position: "absolute", right: tokens.spacing.sm, width: 40, zIndex: 2 },
  equivalence: { alignSelf: "flex-end", color: tokens.color.textMuted, fontSize: tokens.type.caption, marginBottom: 4, marginRight: tokens.layout.reducedInset - tokens.card.outerPadding + 4, marginTop: 1, textAlign: "right" },
  field: { gap: 7 },
  inlinePicker: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, marginBottom: tokens.layout.reducedInset - 6, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, overflow: "hidden", position: "relative" },
  iosPicker: { color: tokens.color.textMain, height: nativeWheelMetrics.height, width: "100%" },
  label: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  labelRow: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  measurePickerColumn: { flex: 0, width: 150 },
  pickerItem: { color: tokens.color.textMain, fontSize: nativeWheelMetrics.fontSize },
  pickers: { alignItems: "center", flexDirection: "row", justifyContent: "center" },
  pressed: { opacity: 0.72 },
  row: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  selector: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, flexDirection: "row", gap: 3, justifyContent: "center", marginLeft: 8, marginRight: tokens.layout.reducedInset - tokens.card.outerPadding, maxWidth: 180, minHeight: 36, minWidth: 96, paddingHorizontal: 10 },
  selectorText: { color: tokens.color.textMain, flexShrink: 1, fontSize: 16, textAlign: "center" },
});
