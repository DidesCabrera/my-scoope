import { Picker } from "@react-native-picker/picker";
import { Platform, StyleSheet, View } from "react-native";

import { nativeWheelMetrics } from "@/components/ui/native-wheel-metrics";
import { tokens } from "@/design/tokens";
import { householdAmounts, householdMeasures, type HouseholdEquivalencePickerProps, type HouseholdMeasure } from "./household-equivalence-picker.types";

export function HouseholdEquivalencePicker({ amount, measure, onAmountChange, onMeasureChange }: HouseholdEquivalencePickerProps) {
  const selectedAmount = Number(amount);
  const amounts = Number.isFinite(selectedAmount) && selectedAmount > 0 && !householdAmounts.includes(selectedAmount)
    ? [...householdAmounts, selectedAmount].sort((a, b) => a - b)
    : householdAmounts;
  const pickerStyle = Platform.OS === "ios" ? styles.iosPicker : styles.androidPicker;

  return (
    <View accessibilityLabel="Cantidad y medida de equivalencia cotidiana" style={styles.container}>
      <View style={styles.amountColumn}>
        <Picker accessibilityLabel="Cantidad de medidas" dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(value) => onAmountChange(String(value))} selectedValue={selectedAmount} style={pickerStyle}>
          {amounts.map((value) => <Picker.Item key={value} label={value.toLocaleString("es-CL", { maximumFractionDigits: 3 })} value={value} />)}
        </Picker>
      </View>
      <View style={styles.measureColumn}>
        <Picker accessibilityLabel="Medida cotidiana" dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(value) => onMeasureChange(value as HouseholdMeasure)} selectedValue={measure} style={pickerStyle}>
          {householdMeasures.map(({ value, label }) => <Picker.Item key={value || "none"} label={label} value={value} />)}
        </Picker>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.panel, flexDirection: "row", justifyContent: "center", marginHorizontal: -6, overflow: "hidden" },
  amountColumn: { width: 110 },
  measureColumn: { flex: 1, maxWidth: 190 },
  iosPicker: { color: tokens.color.textMain, height: nativeWheelMetrics.height, width: "100%" },
  androidPicker: { color: tokens.color.textMain, minHeight: 54, width: "100%" },
  pickerItem: { color: tokens.color.textMain, fontSize: nativeWheelMetrics.fontSize },
});
