import type { PropsWithChildren, ReactNode } from "react";
import { CalendarDays, CalendarRange, Carrot, ClipboardList, Utensils, type LucideIcon } from "lucide-react-native";
import { StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";

import type { LibraryEntity, LibraryIndicator } from "@/api/types";
import { Card } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

const entityLabels: Record<LibraryEntity, string> = {
  food: "Alimento",
  meal: "Comida",
  dailyPlan: "Plan diario",
  program: "Programa",
};

const entityIcons: Record<LibraryEntity, LucideIcon> = {
  food: Carrot,
  meal: Utensils,
  dailyPlan: ClipboardList,
  program: CalendarRange,
};

const structuralIcons: Record<NonNullable<LibraryIndicator["icon"]>, LucideIcon> = {
  day: CalendarDays,
  food: Carrot,
  meal: Utensils,
  dailyPlan: ClipboardList,
  week: CalendarRange,
};

const structuralIndicatorColors: Record<NonNullable<LibraryIndicator["icon"]>, string> = {
  day: tokens.color.program,
  food: tokens.color.food,
  meal: tokens.color.meal,
  dailyPlan: tokens.color.dailyPlan,
  week: tokens.color.program,
};

export function EntityIcon({ entity, size = "regular", tone = "entity" }: { entity: LibraryEntity; size?: "compact" | "regular" | "hero"; tone?: "entity" | "white" }) {
  const Icon = entityIcons[entity];
  const compact = size === "compact";
  const hero = size === "hero";
  return (
    <View style={[styles.entityIcon, compact && styles.entityIconCompact, hero && styles.entityIconHero, { backgroundColor: tone === "white" ? "transparent" : tokens.color[entity] }]}> 
      <Icon color={tone === "white" ? tokens.color.textMain : tokens.color.entityIconForeground} size={tone === "white" ? 18 : compact ? 11 : hero ? 22 : 13} strokeWidth={hero ? 1.9 : 2.4} />
    </View>
  );
}

export function StructuralIndicators({ indicators, entity }: { indicators: LibraryIndicator[]; entity?: LibraryEntity }) {
  if (indicators.length === 0) return null;
  return (
    <View accessibilityLabel={indicators.map(({ label, value }) => `${value} ${label}`).join(", ")} accessible style={styles.structuralIndicators}>
      {indicators.map((indicator, index) => {
        const Icon = indicator.icon ? structuralIcons[indicator.icon] : null;
        const color = indicator.icon
          ? structuralIndicatorColors[indicator.icon]
          : entity
            ? tokens.color[entity]
            : tokens.color.textMuted;
        return (
          <View key={`${indicator.icon}-${indicator.label}-${index}`} style={[styles.structuralItem, { backgroundColor: color }]}>
            <Text style={styles.structuralValue}>{indicator.value}</Text>
            {Icon ? <Icon color={tokens.color.entityIconForeground} size={13} strokeWidth={2.2} /> : null}
          </View>
        );
      })}
    </View>
  );
}

export function EntityHeading({ entity, indicators, subtitle, title, variant = "card" }: {
  entity: LibraryEntity;
  indicators?: LibraryIndicator[];
  subtitle?: string;
  title: string;
  variant?: "card" | "page";
}) {
  return (
    <View style={styles.headingCopy}>
      <View style={styles.entityEyebrowRow}>
        <EntityIcon entity={entity} size="compact" />
        <Text style={styles.eyebrow}>{entityLabels[entity]}</Text>
      </View>
      <Text style={[styles.headingTitle, variant === "page" && styles.headingTitlePage]}>{title}</Text>
      {subtitle ? <Text style={styles.headingSubtitle}>{subtitle}</Text> : null}
      {indicators ? <StructuralIndicators entity={entity} indicators={indicators} /> : null}
    </View>
  );
}

export function EntityCard({ children, entity, indicators, style, subtitle, title }: PropsWithChildren<{
  entity: LibraryEntity;
  indicators?: LibraryIndicator[];
  style?: StyleProp<ViewStyle>;
  subtitle?: string;
  title: string;
}>) {
  return (
    <Card accent={tokens.color[entity]} style={[styles.card, style]}>
      <EntityHeading entity={entity} indicators={indicators} subtitle={subtitle} title={title} />
      {children}
    </Card>
  );
}

export function EntityCardPanelSlot({ children }: PropsWithChildren) {
  return <View style={styles.panelSlot}>{children}</View>;
}

export function CollectionPageHeader({ action, count, countIcon, entity, title }: {
  action?: ReactNode;
  count?: number;
  countIcon: LibraryIndicator["icon"];
  entity: LibraryEntity;
  title: string;
}) {
  return (
    <View style={styles.collectionHeader}>
      <View style={styles.collectionIdentity}>
        <EntityIcon entity={entity} size="hero" />
        <Text style={styles.collectionTitle}>{title}</Text>
      </View>
      {count !== undefined ? <StructuralIndicators entity={entity} indicators={[{ icon: countIcon, label: "elementos", value: count }]} /> : null}
      {action}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  headingCopy: { alignItems: "flex-start", gap: tokens.spacing.xs, minWidth: 0 },
  entityEyebrowRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  entityIcon: { alignItems: "center", borderRadius: 5, height: 22, justifyContent: "center", width: 22 },
  entityIconCompact: { height: 18, width: 18 },
  entityIconHero: { borderRadius: tokens.radius.md, height: 40, width: 40 },
  eyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: "700", textTransform: "uppercase" },
  headingTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "600", lineHeight: 25 },
  headingTitlePage: { fontSize: 22, lineHeight: 32 },
  headingSubtitle: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 18 },
  structuralIndicators: { alignItems: "center", alignSelf: "flex-start", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.compact },
  structuralItem: { alignItems: "center", borderRadius: tokens.spacing.compact, flexDirection: "row", gap: tokens.spacing.xs, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  structuralValue: { color: tokens.color.entityIconForeground, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: "500", lineHeight: 15 },
  panelSlot: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minWidth: 0 },
  collectionHeader: { alignItems: "flex-start", gap: tokens.spacing.md, minWidth: 0, paddingVertical: tokens.spacing.md, width: "100%" },
  collectionIdentity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, minWidth: 0, width: "100%" },
  collectionTitle: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.title, fontWeight: "600", lineHeight: 32 },
});
