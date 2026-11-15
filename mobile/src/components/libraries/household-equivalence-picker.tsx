import { StyleSheet, TextInput, View } from "react-native";

import { tokens } from "@/design/tokens";
import { householdMeasures, type HouseholdEquivalencePickerProps, type HouseholdMeasure } from "./household-equivalence-picker.types";

export function HouseholdEquivalencePicker({ amount, measure, onAmountChange, onMeasureChange }: HouseholdEquivalencePickerProps) {
  return (
    <View accessibilityLabel="Cantidad y medida de equivalencia cotidiana" style={styles.container}>
      <TextInput accessibilityLabel="Cantidad de medidas" inputMode="decimal" onChangeText={onAmountChange} style={styles.amount} value={amount} />
      <select aria-label="Medida cotidiana" onChange={(event) => onMeasureChange(event.target.value as HouseholdMeasure)} style={styles.measure} value={measure}>
        {householdMeasures.map(({ value, label }) => <option key={value || "none"} value={value}>{label}</option>)}
      </select>
    </View>
  );
}

const styles = StyleSheet.create({
  amount: { backgroundColor: tokens.color.surfaceMuted, color: tokens.color.textMain, fontSize: 18, minHeight: 54, paddingHorizontal: 16, textAlign: "center", width: 110 },
  container: { borderRadius: tokens.radius.panel, flexDirection: "row", gap: tokens.spacing.sm, marginHorizontal: -6, overflow: "hidden" },
  measure: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.panel, color: tokens.color.textMain, flex: 1, fontSize: 18, minHeight: 54, paddingHorizontal: 12 },
});
