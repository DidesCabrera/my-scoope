import type { PropsWithChildren, ReactNode } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export type EntityPanelTab<T extends string> = { icon?: ReactNode | ((selected: boolean) => ReactNode); iconOnly?: boolean; key: T; label: string };

export function EntityPanelTabs<T extends string>({ activeTab, onChange, tabs }: {
  activeTab: T;
  onChange: (tab: T) => void;
  tabs: EntityPanelTab<T>[];
}) {
  return (
    <ScrollView accessibilityRole="tablist" contentContainerStyle={styles.tabs} horizontal showsHorizontalScrollIndicator={false}>
      {tabs.map((tab) => {
        const selected = tab.key === activeTab;
        return (
          <Pressable
            accessibilityLabel={tab.label}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            key={tab.key}
            onPress={() => onChange(tab.key)}
            style={({ pressed }) => [styles.tab, selected && styles.tabSelected, pressed && styles.pressed]}>
            {typeof tab.icon === "function" ? tab.icon(selected) : tab.icon}
            {!tab.iconOnly ? <Text style={[styles.tabLabel, selected && styles.tabLabelSelected]}>{tab.label}</Text> : null}
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

export function PanelSurface({ children }: PropsWithChildren) {
  return <View style={styles.surface}>{children}</View>;
}

export function PanelBody({ children }: PropsWithChildren) {
  return <View style={styles.body}>{children}</View>;
}

export function PanelEmptyState({ label }: { label: string }) {
  return <Text style={styles.empty}>{label}</Text>;
}

const styles = StyleSheet.create({
  surface: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minWidth: 0, overflow: "hidden" },
  tabs: { gap: tokens.spacing.compact, padding: tokens.spacing.sm },
  tab: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.xs, height: 30, justifyContent: "center", paddingHorizontal: tokens.spacing.md },
  tabSelected: { backgroundColor: tokens.color.textMain, borderColor: "transparent" },
  tabLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, letterSpacing: 0 },
  tabLabelSelected: { color: tokens.color.surfaceApp },
  pressed: { opacity: 0.72 },
  body: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, paddingBottom: tokens.spacing.sm },
  empty: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 18, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.lg, textAlign: "center" },
});
