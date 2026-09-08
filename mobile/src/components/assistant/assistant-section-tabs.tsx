import { type Href, useRouter } from "expo-router";
import { ClipboardCheck, MessageCircle } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export type AssistantSection = "chats" | "proposals";

const sections = [
  { href: "/assistant" as Href, icon: MessageCircle, key: "chats" as const, label: "Chats" },
  { href: "/proposals" as Href, icon: ClipboardCheck, key: "proposals" as const, label: "Propuestas" },
];

export function AssistantSectionTabs({ activeSection }: { activeSection: AssistantSection }) {
  const router = useRouter();
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
            onPress={() => { if (!selected) router.replace(section.href); }}
            style={({ pressed }) => [styles.tab, selected && styles.tabActive, pressed && styles.pressed]}
          >
            <Icon color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />
            <Text style={[styles.tabText, selected && styles.tabTextActive]}>{section.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.65 },
  tab: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "center", minHeight: 30, paddingHorizontal: tokens.spacing.md },
  tabActive: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  tabText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  tabTextActive: { color: tokens.color.surfaceApp },
  tabs: { flexDirection: "row", gap: tokens.spacing.compact },
});
