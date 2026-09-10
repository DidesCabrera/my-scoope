import type { ReactNode } from "react";
import { Pressable, ScrollView, StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";

type TabKey = string | number;

export type TabBarItem<T extends TabKey> = {
  accessibilityLabel?: string;
  count?: number;
  icon?: ReactNode | ((selected: boolean) => ReactNode);
  key: T;
  label: string;
};

type TabBarProps<T extends TabKey> = {
  accessibilityLabel: string;
  activeTab: T;
  onChange(tab: T): void;
  style?: StyleProp<ViewStyle>;
  tabs: readonly TabBarItem<T>[];
};

type ScrollableTabBarProps<T extends TabKey> = TabBarProps<T> & {
  density?: "compact" | "regular";
};

function renderIcon<T extends TabKey>(tab: TabBarItem<T>, selected: boolean) {
  return typeof tab.icon === "function" ? tab.icon(selected) : tab.icon;
}

function TabContent<T extends TabKey>({ selected, tab }: { selected: boolean; tab: TabBarItem<T> }) {
  return (
    <>
      {renderIcon(tab, selected)}
      <Text numberOfLines={1} style={[styles.label, selected && styles.labelSelected]}>{tab.label}</Text>
      {tab.count != null ? <Text style={[styles.count, selected && styles.labelSelected]}>{tab.count}</Text> : null}
    </>
  );
}

export function ScrollableTabBar<T extends TabKey>({ accessibilityLabel, activeTab, density = "regular", onChange, style, tabs }: ScrollableTabBarProps<T>) {
  return (
    <View style={[styles.scrollableViewport, style]}>
      <ScrollView
        accessibilityLabel={accessibilityLabel}
        accessibilityRole="tablist"
        contentContainerStyle={[styles.scrollableContent, density === "compact" && styles.scrollableContentCompact]}
        directionalLockEnabled
        horizontal
        nestedScrollEnabled
        showsHorizontalScrollIndicator={false}
        style={styles.scrollableBar}>
        {tabs.map((tab) => {
          const selected = activeTab === tab.key;
          return (
            <Pressable
              accessibilityLabel={tab.accessibilityLabel}
              accessibilityRole="tab"
              accessibilityState={{ selected }}
              key={tab.key}
              onPress={() => { if (!selected) onChange(tab.key); }}
              style={({ pressed }) => [styles.scrollableTab, density === "compact" && styles.scrollableTabCompact, selected && styles.tabSelected, pressed && styles.pressed]}>
              <TabContent selected={selected} tab={tab} />
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

export function DistributedTabBar<T extends TabKey>({ accessibilityLabel, activeTab, onChange, style, tabs }: TabBarProps<T>) {
  return (
    <View accessibilityLabel={accessibilityLabel} accessibilityRole="tablist" style={[styles.distributedBar, style]}>
      {tabs.map((tab) => {
        const selected = activeTab === tab.key;
        return (
          <Pressable
            accessibilityLabel={tab.accessibilityLabel}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            key={tab.key}
            onPress={() => { if (!selected) onChange(tab.key); }}
            style={({ pressed }) => [styles.distributedTab, selected && styles.tabSelected, pressed && styles.pressed]}>
            <TabContent selected={selected} tab={tab} />
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  count: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.medium },
  distributedBar: { flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0, width: "100%" },
  distributedTab: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, flex: 1, flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "center", minHeight: 34, minWidth: 0, paddingHorizontal: tokens.spacing.sm },
  label: { color: tokens.color.textMuted, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium },
  labelSelected: { color: tokens.color.surfaceApp },
  pressed: { opacity: 0.68 },
  scrollableBar: { flexGrow: 0, width: "100%" },
  scrollableContent: { flexDirection: "row", gap: tokens.spacing.sm },
  scrollableContentCompact: { gap: tokens.spacing.compact },
  scrollableTab: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "center", minHeight: 40, paddingHorizontal: tokens.spacing.md },
  scrollableTabCompact: { backgroundColor: tokens.color.surfaceApp, borderColor: tokens.color.borderDefault, minHeight: 30 },
  scrollableViewport: { flexShrink: 1, minWidth: 0, width: "100%" },
  tabSelected: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
});
