import { Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export function SupplementChoiceGrid<T extends string>({ label, onChange, options, value }: {
  label: string;
  onChange(value: T): void;
  options: { label: string; value: T }[];
  value: T;
}) {
  return <View style={styles.group}>
    <Text style={styles.label}>{label}</Text>
    <View style={styles.options}>{options.map((option) => {
      const selected = option.value === value;
      return <Pressable accessibilityRole="radio" accessibilityState={{ selected }} key={option.value} onPress={() => onChange(option.value)} style={[styles.option, selected && styles.selected]}>
        <Text style={[styles.optionText, selected && styles.selectedText]}>{option.label}</Text>
      </Pressable>;
    })}</View>
  </View>;
}

const styles = StyleSheet.create({
  group: { gap: tokens.spacing.sm },
  label: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  option: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, minHeight: 42, justifyContent: "center", paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.sm },
  optionText: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  options: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  selected: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  selectedText: { color: tokens.color.surfaceApp },
});
