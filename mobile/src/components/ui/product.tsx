import type { PropsWithChildren, ReactNode } from "react";
import {
  CalendarDays,
  CalendarRange,
  Carrot,
  ClipboardList,
  GitCompareArrows,
  Home,
  Inbox,
  type LucideIcon,
  MessageSquareText,
  UserRound,
  Utensils,
} from "lucide-react-native";
import { Pressable, StyleProp, StyleSheet, Text, useWindowDimensions, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";
import { Button } from "./controls";
import { Card } from "./surfaces";

export type EntityKind = "food" | "meal" | "dailyPlan" | "dpm" | "program" | "proposal" | "inbox" | "comparator" | "home" | "profile";

export type StructuralIndicatorKind = "day" | "food" | "meal" | "week";

export type StructuralIndicator = {
  icon: StructuralIndicatorKind;
  label: string;
  value: number | string;
};

const entityLabels: Record<EntityKind, string> = {
  food: "Alimento",
  meal: "Comida",
  dailyPlan: "Plan diario",
  dpm: "Plan diario",
  program: "Programa",
  proposal: "Propuesta",
  inbox: "Bandeja",
  comparator: "Comparador",
  home: "Inicio",
  profile: "Perfil",
};

const entityIcons: Record<EntityKind, LucideIcon> = {
  food: Carrot,
  meal: Utensils,
  dailyPlan: ClipboardList,
  dpm: CalendarDays,
  program: CalendarRange,
  proposal: MessageSquareText,
  inbox: Inbox,
  comparator: GitCompareArrows,
  home: Home,
  profile: UserRound,
};

const structuralIcons: Record<StructuralIndicatorKind, LucideIcon> = {
  day: CalendarDays,
  food: Carrot,
  meal: Utensils,
  week: CalendarRange,
};

export function EntityIcon({ entity, size = "regular" }: { entity: EntityKind; size?: "compact" | "regular" }) {
  const Icon = entityIcons[entity];
  const compact = size === "compact";
  return (
    <View style={[styles.entityIcon, compact && styles.entityIconCompact, { backgroundColor: tokens.color[entity] }]}>
      <Icon color={tokens.color.entityIconForeground} size={compact ? 11 : 13} strokeWidth={2.4} />
    </View>
  );
}

export function StructuralIndicators({ indicators }: { indicators: StructuralIndicator[] }) {
  if (indicators.length === 0) return null;
  return (
    <View
      accessibilityLabel={indicators.map(({ label, value }) => `${value} ${label}`).join(", ")}
      accessible
      style={styles.structuralIndicators}>
      {indicators.map((indicator, index) => {
        const Icon = structuralIcons[indicator.icon];
        return (
          <View key={`${indicator.icon}-${indicator.label}-${index}`} style={styles.structuralFragment}>
            {index > 0 ? <View style={styles.structuralDivider} /> : null}
            <View style={styles.structuralItem}>
              <Text style={styles.structuralValue}>{indicator.value}</Text>
              <Icon color={tokens.color.structuralIndicatorForeground} size={13} strokeWidth={2.2} />
            </View>
          </View>
        );
      })}
    </View>
  );
}

export function EntityHeading({
  title,
  entity,
  eyebrow,
  subtitle,
  indicators,
  accessory,
  variant = "card",
}: {
  title: string;
  entity: EntityKind;
  eyebrow?: string;
  subtitle?: string;
  indicators?: StructuralIndicator[];
  accessory?: ReactNode;
  variant?: "card" | "page";
}) {
  const { width } = useWindowDimensions();
  const page = variant === "page";
  const pageTitleSize = width < 420 ? 22 : 24;
  const pageTitleLineHeight = width < 420 ? 32 : 34;
  return (
    <View style={styles.headingRow}>
      <View style={styles.headingCopy}>
        <View style={styles.entityEyebrowRow}>
          <EntityIcon entity={entity} size="compact" />
          <Text style={styles.eyebrow}>{eyebrow ?? entityLabels[entity]}</Text>
        </View>
        <Text style={[styles.headingTitle, page && { fontSize: pageTitleSize, lineHeight: pageTitleLineHeight }]}>{title}</Text>
        {subtitle ? <Text style={styles.headingSubtitle}>{subtitle}</Text> : null}
        {indicators ? <StructuralIndicators indicators={indicators} /> : null}
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
  indicators,
  accessory,
  children,
  onPress,
  style,
}: PropsWithChildren<{
  entity: EntityKind;
  title: string;
  eyebrow?: string;
  subtitle?: string;
  indicators?: StructuralIndicator[];
  accessory?: ReactNode;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}>) {
  const content = (
    <Card accent={tokens.color[entity]} style={[onPress && styles.entityCardInPressable, style]}>
      <EntityHeading accessory={accessory} entity={entity} eyebrow={eyebrow} indicators={indicators} subtitle={subtitle} title={title} />
      {children}
    </Card>
  );
  if (!onPress) return content;
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.entityCardPressable, pressed && styles.pressed]}>
      {content}
    </Pressable>
  );
}

export function EntityCardPanelSlot({ children }: PropsWithChildren) {
  return <View style={styles.entityCardPanelSlot}>{children}</View>;
}

export function CardHeader({
  title,
  description,
  accessory,
  density = "regular",
}: {
  title: string;
  description?: string;
  accessory?: ReactNode;
  density?: "compact" | "regular";
}) {
  const compact = density === "compact";
  return (
    <View style={[styles.cardHeader, compact && styles.cardHeaderCompact]}>
      <View style={[styles.cardHeaderCopy, compact && styles.cardHeaderCopyCompact]}>
        <Text style={[styles.cardHeaderTitle, compact && styles.cardHeaderTitleCompact]}>{title}</Text>
        {description ? (
          <Text style={[styles.cardHeaderDescription, compact && styles.cardHeaderDescriptionCompact]}>
            {description}
          </Text>
        ) : null}
      </View>
      {accessory}
    </View>
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
      {title ? <CardHeader accessory={action} description={description} title={title} /> : null}
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
      <CardHeader accessory={action} density="compact" description={description} title={title} />
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
  entityCardPressable: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  entityCardInPressable: { marginHorizontal: 0 },
  headingRow: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md },
  headingCopy: { alignItems: "flex-start", flex: 1, gap: tokens.spacing.xs, minWidth: 0 },
  entityEyebrowRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  entityIcon: { alignItems: "center", borderRadius: 5, height: 22, justifyContent: "center", width: 22 },
  entityIconCompact: { height: 18, width: 18 },
  eyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, letterSpacing: 0, textTransform: "uppercase" },
  headingTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 25 },
  headingSubtitle: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 18 },
  structuralIndicators: { alignItems: "center", alignSelf: "flex-start", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.sm, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.compact, paddingHorizontal: tokens.spacing.compact, paddingVertical: tokens.spacing.xs },
  structuralFragment: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  structuralItem: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  structuralValue: { color: tokens.color.structuralIndicatorForeground, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.medium, letterSpacing: 0, lineHeight: 15 },
  structuralDivider: { backgroundColor: tokens.color.borderDefault, height: 12, width: 1 },
  entityCardPanelSlot: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minWidth: 0 },
  cardHeader: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  cardHeaderCompact: { gap: tokens.spacing.sm },
  cardHeaderCopy: { flex: 1, gap: tokens.spacing.xs },
  cardHeaderCopyCompact: { gap: 2 },
  cardHeaderTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 21 },
  cardHeaderTitleCompact: { fontSize: tokens.type.caption, lineHeight: 18 },
  cardHeaderDescription: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0, lineHeight: 18 },
  cardHeaderDescriptionCompact: { fontSize: tokens.type.label, lineHeight: 16 },
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
