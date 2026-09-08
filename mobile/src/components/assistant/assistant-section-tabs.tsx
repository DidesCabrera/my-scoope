import { ClipboardCheck, MessageCircle } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export type AssistantSection = "chats" | "proposals";

const sections = [
  { icon: MessageCircle, key: "chats" as const, label: "Chats" },
  { icon: ClipboardCheck, key: "proposals" as const, label: "Propuestas" },
];

export function AssistantSectionTabs({ activeSection, counts, onChange }: { activeSection: AssistantSection; counts: Record<AssistantSection, number>; onChange(section: AssistantSection): void }) {
  return (
    <View accessibilityLabel="Secciones del Asistente AI" accessibilityRole="tablist" style={styles.tabs}>
      {sections.map((section) => {
        const selected = section.key === activeSection;
        const Icon = section.icon;
        return (
          <Pressable
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            key={section.key}
            onPress={() => { if (!selected) onChange(section.key); }}
            style={({ pressed }) => [styles.tab, selected && styles.tabActive, pressed && styles.pressed]}
          >
            <View style={styles.identity}>
              <Icon color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />
              <Text style={[styles.tabText, selected && styles.tabTextActive]}>{section.label}</Text>
            </View>
            <Text style={[styles.count, selected && styles.countActive]}>{counts[section.key]}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  count: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: "800" },
  countActive: { color: tokens.color.surfaceApp },
  identity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  pressed: { opacity: 0.65 },
  tab: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, flex: 1, flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "space-between", minHeight: 38, paddingHorizontal: tokens.spacing.md },
  tabActive: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  tabText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  tabTextActive: { color: tokens.color.surfaceApp },
  tabs: { flexDirection: "row", gap: tokens.spacing.compact, width: "100%" },
});
