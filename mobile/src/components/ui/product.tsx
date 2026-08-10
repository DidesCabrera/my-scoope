import type { PropsWithChildren, ReactNode } from "react";
import { Pressable, StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";
import { Button } from "./controls";
import { Card } from "./surfaces";

export type EntityKind = "food" | "meal" | "dailyPlan" | "dpm" | "program" | "proposal" | "inbox" | "comparator" | "home" | "profile";

export function EntityHeading({
  title,
  entity,
  eyebrow,
  subtitle,
  accessory,
}: {
  title: string;
  entity: EntityKind;
  eyebrow?: string;
  subtitle?: string;
  accessory?: ReactNode;
}) {
  const color = tokens.color[entity];
  return (
    <View style={styles.headingRow}>
      <View style={[styles.entityMarker, { backgroundColor: color }]} />
      <View style={styles.headingCopy}>
        {eyebrow ? <Text style={[styles.eyebrow, { color }]}>{eyebrow}</Text> : null}
        <Text style={styles.headingTitle}>{title}</Text>
        {subtitle ? <Text style={styles.headingSubtitle}>{subtitle}</Text> : null}
      </View>
      {accessory}
    </View>
  );
}

export function EntityCard({
  entity,
  title,
  eyebrow,
  subtitle,
  accessory,
  children,
  onPress,
  style,
}: PropsWithChildren<{
  entity: EntityKind;
  title: string;
  eyebrow?: string;
  subtitle?: string;
  accessory?: ReactNode;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}>) {
  const content = (
    <Card accent={tokens.color[entity]} style={style}>
      <EntityHeading accessory={accessory} entity={entity} eyebrow={eyebrow} subtitle={subtitle} title={title} />
      {children}
    </Card>
  );
  if (!onPress) return content;
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => pressed && styles.pressed}>
      {content}
    </Pressable>
  );
}

export function ContentPanel({
  title,
  description,
  action,
  muted = false,
  children,
}: PropsWithChildren<{ title?: string; description?: string; action?: ReactNode; muted?: boolean }>) {
  return (
    <Card muted={muted}>
      {title ? (
        <View style={styles.panelHeader}>
          <View style={styles.panelCopy}>
            <Text style={styles.panelTitle}>{title}</Text>
            {description ? <Text style={styles.panelDescription}>{description}</Text> : null}
          </View>
          {action}
        </View>
      ) : null}
      {children}
    </Card>
  );
}

export function PanelTabs<T extends string>({
  tabs,
  activeTab,
  onChange,
}: {
  tabs: { key: T; label: string; count?: number }[];
  activeTab: T;
  onChange: (tab: T) => void;
}) {
  return (
    <View accessibilityRole="tablist" style={styles.tabs}>
      {tabs.map((tab) => {
        const selected = tab.key === activeTab;
        return (
          <Pressable
            key={tab.key}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            onPress={() => onChange(tab.key)}
            style={({ pressed }) => [styles.tab, selected && styles.tabSelected, pressed && styles.pressed]}>
            <Text style={[styles.tabText, selected && styles.tabTextSelected]}>{tab.label}</Text>
            {tab.count !== undefined ? <Text style={[styles.tabCount, selected && styles.tabTextSelected]}>{tab.count}</Text> : null}
          </Pressable>
        );
      })}
    </View>
  );
}

export function DetailSection({
  title,
  description,
  action,
  children,
}: PropsWithChildren<{ title: string; description?: string; action?: ReactNode }>) {
  return (
    <View style={styles.detailSection}>
      <View style={styles.panelHeader}>
        <View style={styles.panelCopy}>
          <Text style={styles.panelTitle}>{title}</Text>
          {description ? <Text style={styles.panelDescription}>{description}</Text> : null}
        </View>
        {action}
      </View>
      {children}
    </View>
  );
}

export function CollectionEmptyState({
  title,
  description,
  actionLabel,
  onAction,
}: {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <View style={styles.emptyState}>
      <Text style={styles.emptySymbol}>＋</Text>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyDescription}>{description}</Text>
      {actionLabel && onAction ? <Button label={actionLabel} onPress={onAction} variant="secondary" /> : null}
    </View>
  );
}

export function MessageCard({
  tone = "info",
  title,
  children,
}: PropsWithChildren<{ tone?: "info" | "success" | "warning" | "danger"; title: string }>) {
  const color = tone === "success" ? tokens.color.success : tone === "warning" ? tokens.color.warning : tone === "danger" ? tokens.color.danger : tokens.color.interactivePrimary;
  return (
    <View style={[styles.message, { borderLeftColor: color }]}>
      <Text style={[styles.messageTitle, { color }]}>{title}</Text>
      <Text style={styles.messageBody}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.72 },
  headingRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  entityMarker: { borderRadius: tokens.radius.pill, height: 34, width: 5 },
  headingCopy: { flex: 1, gap: 2 },
  eyebrow: { fontSize: tokens.type.label, fontWeight: "900", letterSpacing: 1, textTransform: "uppercase" },
  headingTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  headingSubtitle: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 18 },
  panelHeader: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  panelCopy: { flex: 1, gap: tokens.spacing.xs },
  panelTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  panelDescription: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  tabs: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, flexDirection: "row", gap: tokens.spacing.xs, padding: tokens.spacing.xs },
  tab: { alignItems: "center", borderRadius: tokens.radius.md, flex: 1, flexDirection: "row", gap: 5, justifyContent: "center", minHeight: 44, paddingHorizontal: tokens.spacing.sm },
  tabSelected: { backgroundColor: tokens.color.textMain },
  tabText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "800" },
  tabTextSelected: { color: tokens.color.surfaceApp },
  tabCount: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontVariant: ["tabular-nums"] },
  detailSection: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, gap: tokens.spacing.md, paddingTop: tokens.spacing.lg },
  emptyState: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderStyle: "dashed", borderWidth: 1, gap: tokens.spacing.sm, padding: tokens.spacing.xxl },
  emptySymbol: { color: tokens.color.textSoft, fontSize: tokens.type.hero, fontWeight: "300" },
  emptyTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800", textAlign: "center" },
  emptyDescription: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23, textAlign: "center" },
  message: { backgroundColor: tokens.color.surfaceMuted, borderLeftWidth: 4, borderRadius: tokens.radius.md, gap: tokens.spacing.xs, padding: tokens.spacing.md },
  messageTitle: { fontSize: tokens.type.caption, fontWeight: "900", letterSpacing: 0.3 },
  messageBody: { color: tokens.color.textMuted, fontSize: 14, lineHeight: 20 },
});
