import * as Haptics from "expo-haptics";
import { Check, GripVertical, Trash2 } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { NestableDraggableFlatList, ScaleDecorator } from "react-native-draggable-flatlist";

import type { LibraryItem } from "@/api/types";
import { EntityIcon } from "@/components/ui";
import { tokens } from "@/design/tokens";

type LibraryListEditorProps = {
  busy: boolean;
  items: LibraryItem[];
  onDelete(item: LibraryItem): void;
  onReorder(items: LibraryItem[]): Promise<void>;
  onToggle(item: LibraryItem): void;
  selectedIds: ReadonlySet<number>;
};

function beginDrag(drag: () => void) {
  void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Rigid).catch(() => undefined);
  drag();
}

export function LibraryListEditor({ busy, items, onDelete, onReorder, onToggle, selectedIds }: LibraryListEditorProps) {
  const selectionActive = selectedIds.size > 0;
  return (
    <View style={styles.table}>
      <NestableDraggableFlatList
        activationDistance={12}
        data={items}
        keyExtractor={(item) => `${item.entity}-${item.id}`}
        onDragEnd={({ data, from, to }) => {
          if (from !== to) void onReorder(data);
        }}
        removeClippedSubviews={false}
        renderItem={({ drag, getIndex, isActive, item }) => {
          const index = getIndex() ?? 0;
          return (
            <ScaleDecorator activeScale={1.018}>
              <View style={[styles.row, isActive && styles.activeRow, index === items.length - 1 && styles.lastRow]}>
                <Pressable
                  accessibilityHint="Mantén pulsado y arrastra para cambiar la posición"
                  accessibilityLabel={`Reordenar ${item.name}`}
                  accessibilityRole="button"
                  delayLongPress={180}
                  disabled={busy || selectionActive}
                  hitSlop={8}
                  onLongPress={() => beginDrag(drag)}
                  style={({ pressed }) => [styles.dragHandle, (busy || selectionActive) && styles.disabled, pressed && styles.pressed]}>
                  <GripVertical color={tokens.color.textMuted} size={19} strokeWidth={2.2} />
                </Pressable>
                <View style={styles.itemColumn}>
                  <EntityIcon entity={item.entity} size="compact" />
                  <Text numberOfLines={2} style={styles.itemName}>{item.name}</Text>
                </View>
                <View style={styles.rowActions}>
                  <Pressable
                    accessibilityLabel={`${selectedIds.has(item.id) ? "Deseleccionar" : "Seleccionar"} ${item.name} para eliminar`}
                    accessibilityRole="checkbox"
                    accessibilityState={{ checked: selectedIds.has(item.id), disabled: busy }}
                    disabled={busy}
                    hitSlop={8}
                    onPress={() => onToggle(item)}
                    style={({ pressed }) => [styles.checkboxButton, selectedIds.has(item.id) && styles.checkboxButtonSelected, busy && styles.disabled, pressed && styles.pressed]}>
                    {selectedIds.has(item.id) ? <Check color={tokens.color.danger} size={16} strokeWidth={3} /> : null}
                  </Pressable>
                  <Pressable
                    accessibilityLabel={`Eliminar ${item.name}`}
                    accessibilityRole="button"
                    disabled={busy}
                    hitSlop={8}
                    onPress={() => onDelete(item)}
                    style={({ pressed }) => [styles.deleteButton, busy && styles.disabled, pressed && styles.pressed]}>
                    <Trash2 color={tokens.color.danger} size={17} />
                  </Pressable>
                </View>
              </View>
            </ScaleDecorator>
          );
        }}
        scrollEnabled={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  activeRow: { backgroundColor: tokens.color.surfaceMuted, elevation: 4, shadowColor: "#000000", shadowOffset: { height: 2, width: 0 }, shadowOpacity: 0.14, shadowRadius: 4 },
  checkboxButton: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.sm, borderWidth: 1.5, height: 24, justifyContent: "center", marginHorizontal: tokens.spacing.sm, width: 24 },
  checkboxButtonSelected: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.danger },
  deleteButton: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 36, justifyContent: "center", width: 36 },
  disabled: { opacity: 0.4 },
  dragHandle: { alignItems: "center", height: 40, justifyContent: "center", width: 34 },
  itemColumn: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  itemName: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, fontWeight: tokens.weight.bold, lineHeight: 21 },
  lastRow: { borderBottomWidth: 0 },
  pressed: { opacity: 0.65 },
  row: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 60, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  rowActions: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  table: { borderBottomColor: tokens.color.borderDefault, borderBottomWidth: 1, borderRadius: 0, borderTopColor: tokens.color.borderDefault, borderTopWidth: 1, marginHorizontal: -tokens.spacing.screen, overflow: "hidden" },
});
