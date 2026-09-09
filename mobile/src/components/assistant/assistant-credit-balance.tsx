import { Sparkles } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";

import type { AssistantAvailability } from "@/api/types";
import { Card, Pill } from "@/components/ui";
import { tokens } from "@/design/tokens";

export function AssistantCreditBalance({ availability }: { availability: AssistantAvailability }) {
  return (
    <Card style={styles.card}>
      <View style={styles.header}>
        <View style={styles.identity}>
          <View style={styles.icon}>
            <Sparkles color={tokens.color.surfaceApp} size={15} strokeWidth={2.2} />
          </View>
          <Text style={styles.title}>Saldo de créditos</Text>
        </View>
        <Pill color={availability.is_available ? tokens.color.success : tokens.color.warning} label={availability.label} />
      </View>
      <View accessibilityLabel={`${availability.available_credits} créditos disponibles`} accessible style={styles.balance}>
        <Text style={styles.value}>{availability.available_credits}</Text>
        <Text style={styles.unit}>créditos disponibles</Text>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  balance: { alignItems: "baseline", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.compact },
  card: { gap: tokens.spacing.sm, marginBottom: tokens.spacing.sm, paddingVertical: tokens.spacing.md },
  header: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "space-between", minWidth: 0 },
  icon: { alignItems: "center", backgroundColor: tokens.color.interactivePrimary, borderRadius: tokens.radius.md, height: 28, justifyContent: "center", width: 28 },
  identity: { alignItems: "center", flexDirection: "row", flexShrink: 1, gap: tokens.spacing.sm, minWidth: 0 },
  title: { color: tokens.color.textMuted, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  unit: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium },
  value: { color: tokens.color.textMain, fontSize: 26, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, lineHeight: 30 },
});
