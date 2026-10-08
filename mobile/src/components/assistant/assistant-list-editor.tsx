import { Check, ClipboardCheck, MessageCircle, Trash2 } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export type AssistantListItem = { id: number; title: string };

type Props<T extends AssistantListItem> = {
  busy: boolean;
  items: T[];
  kind: "chat" | "proposal";
  onDelete(item: T): void;
  onToggle(item: T): void;
  selectedIds: ReadonlySet<number>;
};

export function AssistantListEditor<T extends AssistantListItem>({ busy, items, kind, onDelete, onToggle, selectedIds }: Props<T>) {
  const Icon = kind === "chat" ? MessageCircle : ClipboardCheck;
  return (
    <View style={styles.table}>
      {items.map((item, index) => (
              <View key={`${kind}-${item.id}`} style={[styles.row, index === items.length - 1 && styles.lastRow]}>
                <View style={styles.itemColumn}>
                  <Icon color={tokens.color.textMain} size={19} strokeWidth={2.1} />
                  <Text numberOfLines={2} style={styles.itemName}>{item.title}</Text>
                </View>
                <View style={styles.rowActions}>
                  <Pressable
                    accessibilityLabel={`${selectedIds.has(item.id) ? "Deseleccionar" : "Seleccionar"} ${item.title} para eliminar`}
                    accessibilityRole="checkbox"
                    accessibilityState={{ checked: selectedIds.has(item.id), disabled: busy }}
                    disabled={busy}
                    hitSlop={8}
                    onPress={() => onToggle(item)}
                    style={({ pressed }) => [styles.checkboxButton, selectedIds.has(item.id) && styles.checkboxButtonSelected, busy && styles.disabled, pressed && styles.pressed]}>
                    {selectedIds.has(item.id) ? <Check color={tokens.color.danger} size={16} strokeWidth={3} /> : null}
                  </Pressable>
                  <Pressable
                    accessibilityLabel={`Eliminar ${item.title}`}
                    accessibilityRole="button"
                    disabled={busy}
                    hitSlop={8}
                    onPress={() => onDelete(item)}
                    style={({ pressed }) => [styles.deleteButton, busy && styles.disabled, pressed && styles.pressed]}>
                    <Trash2 color={tokens.color.danger} size={17} />
                  </Pressable>
                </View>
              </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  checkboxButton: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.sm, borderWidth: 1.5, height: 24, justifyContent: "center", marginHorizontal: tokens.spacing.sm, width: 24 },
  checkboxButtonSelected: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.danger },
  deleteButton: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 36, justifyContent: "center", width: 36 },
  disabled: { opacity: 0.4 },
  itemColumn: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  itemName: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, fontWeight: tokens.weight.bold, lineHeight: 21 },
  lastRow: { borderBottomWidth: 0 },
  pressed: { opacity: 0.65 },
  row: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 60, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  rowActions: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  table: { borderBottomColor: tokens.color.borderDefault, borderBottomWidth: 1, borderRadius: 0, borderTopColor: tokens.color.borderDefault, borderTopWidth: 1, marginHorizontal: -tokens.spacing.screen, overflow: "hidden" },
});
