import type { ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export type KeyValueTableItem = {
  accessibilityLabel?: string;
  accessory?: ReactNode;
  icon?: ReactNode;
  id?: number | string;
  label: string;
  onPress?: () => void;
  value: string;
};

function TableRow({ item, last }: { item: KeyValueTableItem; last: boolean }) {
  const content = <>
      <View style={styles.identity}>
        {item.icon}
        <Text style={styles.label}>{item.label}</Text>
      </View>
      <Text adjustsFontSizeToFit minimumFontScale={0.72} numberOfLines={1} style={styles.value}>{item.value}</Text>
      {item.accessory}
    </>;
  return item.onPress ? (
    <Pressable accessibilityLabel={item.accessibilityLabel} accessibilityRole="button" onPress={item.onPress} style={({ pressed }) => [styles.row, last && styles.rowLast, pressed && styles.rowPressed]}>
      {content}
    </Pressable>
  ) : <View style={[styles.row, last && styles.rowLast]}>{content}</View>;
}

export function KeyValueTable({ items }: { items: KeyValueTableItem[] }) {
  return (
    <View style={styles.rows}>
      {items.map((item, index) => (
        <TableRow
          item={item}
          key={item.id ?? item.label}
          last={index === items.length - 1}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  identity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  label: { color: tokens.color.textMuted, flexShrink: 1, fontSize: 14, lineHeight: 20 },
  row: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 46, paddingVertical: tokens.spacing.xs },
  rowLast: { borderBottomWidth: 0 },
  rowPressed: { opacity: 0.65 },
  rows: { marginTop: -tokens.spacing.xs },
  value: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontWeight: tokens.weight.bold, lineHeight: 20, textAlign: "right" },
});
