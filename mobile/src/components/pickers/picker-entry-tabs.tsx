import { Bookmark, Plus } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

type PickerEntryTab = "library" | "create";

export function PickerEntryTabs({ createLabel, onCreate }: { createLabel: string; onCreate(): void }) {
  return (
    <View accessibilityLabel="Origen de la selección" accessibilityRole="tablist" style={styles.entryTabsBar}>
      {([
        { icon: Bookmark, key: "library", label: "Mi librería" },
        { icon: Plus, key: "create", label: createLabel },
      ] satisfies { icon: typeof Bookmark; key: PickerEntryTab; label: string }[]).map((tab) => {
        const selected = tab.key === "library";
        const Icon = tab.icon;
        return (
          <Pressable
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            key={tab.key}
            onPress={() => { if (tab.key === "create") onCreate(); }}
            style={({ pressed }) => [styles.entryTab, selected && styles.entryTabActive, pressed && styles.pressed]}>
            <Icon color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={16} strokeWidth={2.2} />
            <Text style={[styles.entryTabText, selected && styles.entryTabTextActive]}>{tab.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  entryTab: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, flex: 1, flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "center", minHeight: 34, minWidth: 0, paddingHorizontal: tokens.spacing.sm },
  entryTabActive: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  entryTabText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium },
  entryTabTextActive: { color: tokens.color.surfaceApp },
  entryTabsBar: { backgroundColor: tokens.color.surfaceApp, flexDirection: "row", gap: tokens.spacing.compact, paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.sm },
  pressed: { opacity: 0.68 },
});
