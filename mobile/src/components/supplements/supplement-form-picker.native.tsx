import { Picker } from "@react-native-picker/picker";
import { Check, ChevronDown } from "lucide-react-native";
import { useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import { nativeWheelMetrics } from "@/components/ui/native-wheel-metrics";
import type { SupplementFormPickerProps } from "./supplement-form-picker.types";

export function SupplementFormPicker({ label, onChange, onExpandedChange, options, value }: SupplementFormPickerProps) {
  const [expanded, setExpanded] = useState(false);
  const [draft, setDraft] = useState(value);
  const selectedLabel = options.find((option) => option.value === value)?.label ?? "Seleccionar forma";

  const toggle = () => {
    if (!expanded) setDraft(value);
    setExpanded(!expanded);
    onExpandedChange?.(!expanded);
  };
  const commit = () => {
    onChange(draft);
    setExpanded(false);
    onExpandedChange?.(false);
  };

  return <View style={styles.field}>
    <Text style={styles.label}>{label}</Text>
    <Pressable accessibilityLabel={`${label}: ${selectedLabel}`} accessibilityRole="button" accessibilityState={{ expanded }} onPress={toggle} style={({ pressed }) => [styles.input, pressed && styles.pressed]}>
      <Text style={styles.value}>{selectedLabel}</Text>
      <ChevronDown color={tokens.color.textSoft} size={18} />
    </Pressable>
    {expanded ? <View style={styles.inlinePicker}>
      <Picker accessibilityLabel={`Opciones de ${label.toLowerCase()}`} dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => setDraft(String(next))} selectedValue={draft} style={Platform.OS === "ios" ? styles.iosPicker : styles.androidPicker}>
        {options.map((option) => <Picker.Item key={option.value} label={option.label} value={option.value} />)}
      </Picker>
      <Pressable accessibilityLabel="Confirmar forma" accessibilityRole="button" onPress={commit} style={({ pressed }) => [styles.doneButton, pressed && styles.pressed]}>
        <Check color={tokens.color.supplement} size={22} strokeWidth={2.6} />
      </Pressable>
    </View> : null}
  </View>;
}

const styles = StyleSheet.create({
  androidPicker: { color: tokens.color.textMain, minHeight: 54, width: "100%" },
  doneButton: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.pill, bottom: tokens.spacing.sm, height: 40, justifyContent: "center", position: "absolute", right: tokens.spacing.sm, width: 40, zIndex: 2 },
  field: { gap: tokens.spacing.sm },
  inlinePicker: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, overflow: "hidden", position: "relative" },
  input: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, flexDirection: "row", marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 44, paddingHorizontal: tokens.spacing.lg },
  iosPicker: { color: tokens.color.textMain, height: nativeWheelMetrics.height, width: "100%" },
  label: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  pickerItem: { color: tokens.color.textMain, fontSize: nativeWheelMetrics.fontSize },
  pressed: { opacity: 0.72 },
  value: { color: tokens.color.textMain, flex: 1, fontSize: 17 },
});
