import { ChevronDown } from "lucide-react-native";
import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import type { SupplementFormPickerProps } from "./supplement-form-picker.types";

export function SupplementFormPicker({ label, onChange, onExpandedChange, options, value }: SupplementFormPickerProps) {
  const [expanded, setExpanded] = useState(false);
  const selectedLabel = options.find((option) => option.value === value)?.label ?? "Seleccionar forma";
  const toggle = () => {
    setExpanded(!expanded);
    onExpandedChange?.(!expanded);
  };
  return <View style={styles.field}>
    <Text style={styles.label}>{label}</Text>
    <Pressable accessibilityLabel={`${label}: ${selectedLabel}`} accessibilityRole="button" accessibilityState={{ expanded }} onPress={toggle} style={styles.input}>
      <Text style={styles.value}>{selectedLabel}</Text>
      <ChevronDown color={tokens.color.textSoft} size={18} />
    </Pressable>
    {expanded ? <ScrollView showsVerticalScrollIndicator={false} style={styles.options}>
      {options.map((option) => <Pressable accessibilityRole="radio" accessibilityState={{ selected: option.value === value }} key={option.value} onPress={() => { onChange(option.value); setExpanded(false); onExpandedChange?.(false); }} style={styles.option}>
        <Text style={styles.optionText}>{option.label}</Text>
      </Pressable>)}
    </ScrollView> : null}
  </View>;
}

const styles = StyleSheet.create({
  field: { gap: tokens.spacing.sm },
  input: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, flexDirection: "row", marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 44, paddingHorizontal: tokens.spacing.lg },
  label: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  option: { borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, paddingHorizontal: tokens.spacing.lg, paddingVertical: tokens.spacing.md },
  options: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, maxHeight: 216 },
  optionText: { color: tokens.color.textMain, fontSize: tokens.type.body },
  value: { color: tokens.color.textMain, flex: 1, fontSize: 17 },
});
