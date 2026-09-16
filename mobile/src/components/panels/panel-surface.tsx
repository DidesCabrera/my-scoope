import type { PropsWithChildren, ReactNode } from "react";
import { ChevronDown, ChevronUp } from "lucide-react-native";
import { Pressable, ScrollView, StyleProp, StyleSheet, Text, TextStyle, View, ViewStyle } from "react-native";

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

export function SortablePanelHeaderCell({ align = "center", direction, label, onPress, style, textStyle }: {
  align?: "center" | "left";
  direction?: "asc" | "desc";
  label: string;
  onPress(): void;
  style?: StyleProp<ViewStyle>;
  textStyle?: StyleProp<TextStyle>;
}) {
  const directionLabel = direction === "asc" ? "ascendente" : direction === "desc" ? "descendente" : "original";
  return (
    <Pressable
      accessibilityHint="Pulsa para cambiar el orden. Alterna entre descendente, ascendente y original."
      accessibilityLabel={`Ordenar por ${label}. Orden ${directionLabel}`}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.sortHeaderCell, style, pressed && styles.sortHeaderPressed]}>
      <View style={[styles.sortHeaderContent, align === "left" && styles.sortHeaderContentLeft]}>
        <Text numberOfLines={1} style={[styles.sortHeaderText, textStyle]}>{label}</Text>
        {direction === "asc" ? <ChevronUp color={tokens.color.textMuted} size={12} strokeWidth={2.4} /> : null}
        {direction === "desc" ? <ChevronDown color={tokens.color.textMuted} size={12} strokeWidth={2.4} /> : null}
      </View>
    </Pressable>
  );
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
  sortHeaderCell: { alignSelf: "stretch", justifyContent: "center", minWidth: 0 },
  sortHeaderContent: { alignItems: "center", flexDirection: "row", gap: 2, justifyContent: "center", minWidth: 0 },
  sortHeaderContentLeft: { justifyContent: "flex-start" },
  sortHeaderText: { color: tokens.color.textMuted, flexShrink: 1, fontSize: 10, fontWeight: tokens.weight.semibold, textAlign: "center", textTransform: "uppercase" },
  sortHeaderPressed: { opacity: 0.6 },
});
