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
            style={({ pressed }) => [styles.tab, selected && styles.tabSelected, pressed && styles.pressed]}
          >
            <Icon color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />
            <Text style={[styles.label, selected && styles.labelSelected]}>{section.label}</Text>
            <Text style={[styles.count, selected && styles.labelSelected]}>{counts[section.key]}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  count: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.semibold },
  label: { color: tokens.color.textMuted, flexShrink: 1, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold },
  labelSelected: { color: tokens.color.surfaceApp },
  pressed: { opacity: 0.68 },
  tab: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, flex: 1, flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "center", minHeight: 40, minWidth: 0, paddingHorizontal: tokens.spacing.sm },
  tabSelected: { backgroundColor: tokens.color.textMain, borderColor: "transparent" },
  tabs: { flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0, width: "100%" },
});
