import { Bookmark, Plus } from "lucide-react-native";
import { StyleSheet, View } from "react-native";

import { DistributedTabBar, layoutStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";

type PickerEntryTab = "library" | "create";

export function PickerEntryTabs({ createLabel, onCreate }: { createLabel: string; onCreate(): void }) {
  return (
    <View style={[styles.entryTabsBar, layoutStyles.cardContentBleed]}>
      <DistributedTabBar<PickerEntryTab>
        accessibilityLabel="Origen de la selección"
        activeTab="library"
        onChange={(tab) => { if (tab === "create") onCreate(); }}
        tabs={[
          { icon: (selected) => <Bookmark color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={16} strokeWidth={2.2} />, key: "library", label: "Mi librería" },
          { icon: (selected) => <Plus color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={16} strokeWidth={2.2} />, key: "create", label: createLabel },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  entryTabsBar: { backgroundColor: tokens.color.surfaceApp, minWidth: 0, paddingVertical: tokens.spacing.sm },
});
