import { StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/ui";
import { tokens } from "@/design/tokens";

export type SupplementInformationItem = {
  id: string;
  label: string;
  value: string;
};

export function SupplementInformationTable({ items, labelHeader = "Información", valueHeader = "Valor" }: {
  items: SupplementInformationItem[];
  labelHeader?: string;
  valueHeader?: string;
}) {
  return <Card muted style={styles.card}>
    <View style={styles.table}>
      <View accessibilityRole="header" style={[styles.row, styles.header]}>
        <Text style={[styles.headerText, styles.labelColumn]}>{labelHeader}</Text>
        <Text style={[styles.headerText, styles.valueColumn]}>{valueHeader}</Text>
      </View>
      {items.map((item, index) => <View key={item.id} style={[styles.row, index === items.length - 1 && styles.lastRow]}>
        <Text style={[styles.label, styles.labelColumn]}>{item.label}</Text>
        <Text style={[styles.value, styles.valueColumn]}>{item.value}</Text>
      </View>)}
    </View>
  </Card>;
}

const styles = StyleSheet.create({
  card: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, paddingBottom: tokens.spacing.sm, paddingTop: tokens.spacing.xs + 2 },
  header: { backgroundColor: tokens.color.surfaceMuted, minHeight: 32 },
  headerText: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.semibold, textTransform: "uppercase" },
  label: { color: tokens.color.textMain, fontSize: 14, lineHeight: 20 },
  labelColumn: { flex: 1, minWidth: 0, paddingHorizontal: tokens.spacing.xs, textAlign: "left" },
  lastRow: { borderBottomWidth: 0 },
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", minHeight: 46 },
  table: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  value: { color: tokens.color.textMain, fontSize: 14, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, lineHeight: 20 },
  valueColumn: { flex: 1, minWidth: 0, paddingHorizontal: tokens.spacing.xs, textAlign: "right" },
});
