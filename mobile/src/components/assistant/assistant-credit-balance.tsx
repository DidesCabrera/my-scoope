import { StyleSheet, Text } from "react-native";

import type { AssistantAvailability } from "@/api/types";
import { Card, Pill } from "@/components/ui";
import { tokens } from "@/design/tokens";

export function AssistantCreditBalance({ availability }: { availability: AssistantAvailability }) {
  return (
    <Card style={styles.card}>
      <Text accessibilityLabel={`${availability.available_credits} créditos disponibles`} style={styles.balance}>
        <Text style={styles.value}>{availability.available_credits}</Text> créditos disponibles
      </Text>
      <Pill color={availability.is_available ? tokens.color.success : tokens.color.warning} label={availability.label} />
    </Card>
  );
}

const styles = StyleSheet.create({
  balance: { color: tokens.color.textMuted, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium },
  card: { alignItems: "center", borderRadius: tokens.radius.md, flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "space-between", marginBottom: tokens.spacing.sm, paddingVertical: tokens.spacing.sm },
  value: { color: tokens.color.textMain, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold },
});
