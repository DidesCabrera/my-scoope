import { StyleSheet, Text } from "react-native";

import { tokens } from "@/design/tokens";

type CalorieValueProps = {
  compact?: boolean;
  value: number | string;
};

export function CalorieValue({ compact = false, value }: CalorieValueProps) {
  return <Text style={[styles.value, compact && styles.compact]}>{value}</Text>;
}

const styles = StyleSheet.create({
  value: {
    color: tokens.color.textMain,
    fontSize: 29,
    fontVariant: ["tabular-nums"],
    fontWeight: tokens.weight.bold,
    letterSpacing: 0,
  },
  compact: { fontSize: 23 },
});
