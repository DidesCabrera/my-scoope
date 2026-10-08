import type { PropsWithChildren, ReactNode } from "react";
import {
  CalendarClock,
  CalendarDays,
  CalendarRange,
  Carrot,
  Check,
  CheckCheck,
  CircleFadingPlus,
  CircleUserRound,
  ClipboardCheck,
  ClipboardList,
  Clock,
  FileDown,
  House,
  Inbox,
  type LucideIcon,
  MessageSquarePlus,
  NotebookPen,
  Scale,
  Search,
  Sparkles,
  Utensils,
  Weight,
} from "lucide-react-native";
import { Pressable, StyleProp, StyleSheet, Text, useWindowDimensions, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";
import { Chip } from "./chip";
import { Button } from "./controls";
import { Card } from "./surfaces";

export type EntityKind = "food" | "meal" | "dailyPlan" | "dpm" | "program";
export type SectionKind = "home" | "profile" | "chatNew" | "chat" | "proposal" | "calendarization" | "comparator" | "weight" | "explore" | "inbox" | "create" | "import";

export type StructuralIndicatorKind = "clock" | "day" | "food" | "meal" | "dailyPlan" | "week" | "weight";

export type StructuralIndicator = {
  icon?: StructuralIndicatorKind;
  iconPosition?: "leading" | "trailing";
  label: string;
  tone?: "identity" | "surfaceCard" | "surfaceMuted";
  value: number | string;
};

export type CompletionIndicatorCounts = {
  completedCount?: number;
  noteCount?: number;
};

export type EntityHeadingLink = {
  label: string;
  onPress(): void;
};

function isGramQuantity(value: number | string | undefined): value is string {
  return typeof value === "string" && /^[\d.,]+\s*g$/i.test(value.trim());
}

function FoodGramChip({ value }: { value: string }) {
  return <Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={value} textColor={tokens.color.entityIconForeground} />;
}

export function HeaderMetadataChip({ kind, value }: { kind: "date" | "time"; value: string }) {
  const Icon = kind === "time" ? Clock : CalendarDays;
  return (
    <View accessibilityLabel={`${kind === "time" ? "Hora" : "Fecha"}: ${value}`} accessible style={styles.headerMetadataChip}>
      <Icon color={tokens.color.textMuted} size={11} strokeWidth={2} />
      <Text style={styles.headerMetadataChipText}>{value}</Text>
    </View>
  );
}

export function GuideMetric({ label, onPress, tone = "default", value }: { label?: string; onPress?: () => void; tone?: "default" | "ppk"; value: string }) {
  const content = (
    <>
      <View style={styles.guideMetricCopy}>
        {label ? <Text style={styles.guideMetricLabel}>{label}</Text> : null}
        <View style={styles.guideMetricValueRow}>
          <Text style={[styles.guideMetricValue, tone === "ppk" && styles.guideMetricValuePpk]}>{value}</Text>
        </View>
      </View>
    </>
  );
  const accessibilityLabel = label ? `${label}: ${value}` : value;
  const style = [styles.guideMetric, !label && styles.guideMetricValueOnly, tone === "ppk" && styles.guideMetricPpk];
  if (onPress) {
    return <Pressable accessibilityLabel={accessibilityLabel} accessibilityRole="button" onPress={onPress} style={({ pressed }) => [style, pressed && styles.guideMetricPressed]}>{content}</Pressable>;
  }
  return <View accessibilityLabel={accessibilityLabel} accessible style={style}>{content}</View>;
}

const entityLabels: Record<EntityKind, string> = {
  food: "Alimento",
  meal: "Comida",
  dailyPlan: "Plan diario",
  dpm: "Plan diario",
  program: "Programa",
};

const entityIcons: Record<EntityKind, LucideIcon> = {
  food: Carrot,
  meal: Utensils,
  dailyPlan: ClipboardList,
  dpm: CalendarDays,
  program: CalendarRange,
};

const structuralIcons: Record<StructuralIndicatorKind, LucideIcon> = {
  clock: Clock,
  day: CalendarDays,
  food: Carrot,
  meal: Utensils,
  dailyPlan: ClipboardList,
  week: CalendarRange,
  weight: Weight,
};

const structuralIndicatorColors: Record<StructuralIndicatorKind, string> = {
  clock: tokens.color.meal,
  day: tokens.color.program,
  food: tokens.color.food,
  meal: tokens.color.meal,
  dailyPlan: tokens.color.dailyPlan,
  week: tokens.color.program,
  weight: tokens.color.quantity,
};

const sectionIcons: Record<SectionKind, LucideIcon> = {
  home: House,
  profile: CircleUserRound,
  chatNew: MessageSquarePlus,
  chat: Sparkles,
  proposal: ClipboardCheck,
  calendarization: CalendarClock,
  comparator: Scale,
  weight: Weight,
  explore: Search,
  inbox: Inbox,
  create: CircleFadingPlus,
  import: FileDown,
};

export function EntityIcon({ entity, size = "regular", tone = "entity" }: { entity: EntityKind; size?: "benefit" | "compact" | "regular" | "header" | "hero"; tone?: "entity" | "white" }) {
  const Icon = entityIcons[entity];
  const benefit = size === "benefit";
  const compact = size === "compact";
  const header = size === "header";
  const hero = size === "hero";
  return (
    <View style={[styles.entityIcon, benefit && styles.entityIconBenefit, compact && styles.entityIconCompact, header && styles.entityIconHeader, hero && styles.entityIconHero, { backgroundColor: tone === "white" ? "transparent" : tokens.color[entity] }]}>
      <Icon color={tone === "white" ? tokens.color.textMain : tokens.color.entityIconForeground} size={tone === "white" || header ? 18 : benefit ? 14 : compact ? 11 : hero ? 22 : 13} strokeWidth={hero ? 1.9 : 2.4} />
    </View>
  );
}

export function SectionIcon({ color = tokens.color.textMain, section, size = "regular" }: { color?: string; section: SectionKind; size?: "compact" | "regular" | "hero" }) {
  const Icon = sectionIcons[section];
  const compact = size === "compact";
  const hero = size === "hero";
  return (
    <View style={[styles.sectionIcon, compact && styles.sectionIconCompact, hero && styles.sectionIconHero]}>
      <Icon color={color} size={compact ? 16 : hero ? 28 : 20} strokeWidth={hero ? 1.8 : 2} />
    </View>
  );
}

export function StructuralIndicators({ indicators, entity, tone = "identity" }: { indicators: StructuralIndicator[]; entity?: EntityKind; tone?: "identity" | "surfaceCard" | "surfaceMuted" }) {
  if (indicators.length === 0) return null;
  return (
    <View
      accessibilityLabel={indicators.map(({ label, value }) => `${value} ${label}`).join(", ")}
      accessible
      style={styles.structuralIndicators}>
      {indicators.map((indicator, index) => {
        const key = `${indicator.icon ?? "text"}-${indicator.label}-${index}`;
        if (entity === "food" && isGramQuantity(indicator.value)) {
          return <FoodGramChip key={key} value={indicator.value} />;
        }
        const Icon = indicator.icon ? structuralIcons[indicator.icon] : null;
        const itemTone = indicator.tone ?? tone;
        const color = indicator.icon
          ? structuralIndicatorColors[indicator.icon]
          : entity
            ? tokens.color[entity]
            : tokens.color.textMuted;
        return (
          <View
            key={key}
            style={[
              styles.structuralItem,
              { backgroundColor: itemTone === "surfaceCard" ? tokens.color.surfaceCard : itemTone === "surfaceMuted" ? tokens.color.surfaceMuted : color },
              itemTone !== "identity" && styles.structuralItemSurface,
            ]}>
            {Icon && indicator.iconPosition !== "trailing" ? <Icon color={itemTone === "identity" ? tokens.color.entityIconForeground : tokens.color.textMain} size={13} strokeWidth={2.2} /> : null}
            <Text style={[styles.structuralValue, itemTone !== "identity" && styles.structuralValueSurface]}>{indicator.value}</Text>
            {Icon && indicator.iconPosition === "trailing" ? <Icon color={tokens.color.entityIconForeground} size={13} strokeWidth={2.2} /> : null}
          </View>
        );
      })}
    </View>
  );
}

export function CompletionIndicators({ completedCount = 0, noteCount = 0, summarized = false }: CompletionIndicatorCounts & { summarized?: boolean }) {
  if (completedCount <= 0 && noteCount <= 0) return null;
  const labels = [
    noteCount > 0 ? `${noteCount} ${noteCount === 1 ? "comida con nota" : "comidas con nota"}` : null,
    completedCount > 0 ? `${completedCount} ${completedCount === 1 ? "comida cumplida" : "comidas cumplidas"}` : null,
  ].filter(Boolean).join(", ");
  if (summarized) {
    return (
      <View accessibilityLabel={labels} accessible style={styles.completionIndicators}>
        {noteCount > 0 ? (
          <View style={styles.completionIndicatorSummary}>
            <Text style={styles.completionIndicatorCount}>{noteCount}</Text>
            <NotebookPen color={tokens.color.textMuted} size={17} strokeWidth={2.1} />
          </View>
        ) : null}
        {completedCount > 0 ? (
          <View style={styles.completionIndicatorSummary}>
            <Text style={styles.completionIndicatorCount}>{completedCount}</Text>
            <CheckCheck color={tokens.color.textMuted} size={19} strokeWidth={2.3} />
          </View>
        ) : null}
      </View>
    );
  }
  return (
    <View accessibilityLabel={labels} accessible style={styles.completionIndicators}>
      {Array.from({ length: noteCount }, (_, index) => <NotebookPen color={tokens.color.textMuted} key={`note-${index}`} size={17} strokeWidth={2.1} />)}
      {Array.from({ length: completedCount }, (_, index) => <Check color={tokens.color.textMuted} key={`check-${index}`} size={18} strokeWidth={2.4} />)}
    </View>
  );
}

export function EntityHeading({
  title,
  entity,
  eyebrow,
  subtitle,
  indicators,
  completion,
  accessory,
  eyebrowAccessory,
  headingLink,
  identityIcon: IdentityIcon,
  variant = "card",
}: {
  title: string;
  entity: EntityKind;
  eyebrow?: string;
  subtitle?: string;
  indicators?: StructuralIndicator[];
  completion?: CompletionIndicatorCounts;
  accessory?: ReactNode;
  eyebrowAccessory?: ReactNode;
  headingLink?: EntityHeadingLink;
  identityIcon?: LucideIcon;
  variant?: "card" | "page";
}) {
  const { width } = useWindowDimensions();
  const page = variant === "page";
  const pageTitle = width < 420
    ? tokens.component.entityHeading.pageCompact
    : tokens.component.entityHeading.pageRegular;
  const copy = (
    <>
      <View style={styles.headingEyebrowLine}>
        <View style={styles.entityEyebrowRow}>
          {IdentityIcon ? <View style={[styles.entityIcon, styles.entityIconCompact, { backgroundColor: tokens.color[entity] }]}><IdentityIcon color={tokens.color.entityIconForeground} size={11} strokeWidth={2.4} /></View> : <EntityIcon entity={entity} size="compact" />}
          <Text numberOfLines={1} style={styles.eyebrow}>{eyebrow ?? entityLabels[entity]}</Text>
        </View>
        {eyebrowAccessory}
      </View>
      <Text style={[styles.headingTitle, page && pageTitle]}>{title}</Text>
      {subtitle ? entity === "food" && isGramQuantity(subtitle) ? <FoodGramChip value={subtitle} /> : <Text style={styles.headingSubtitle}>{subtitle}</Text> : null}
      {indicators || completion ? (
        <View style={[styles.headingIndicators, page && styles.headingIndicatorsPage]}>
          {indicators ? <StructuralIndicators entity={entity} indicators={indicators} /> : null}
          {completion ? <CompletionIndicators {...completion} summarized={entity === "dailyPlan"} /> : null}
        </View>
      ) : null}
    </>
  );
  return (
    <View style={styles.headingRow}>
      {headingLink ? (
        <Pressable
          accessibilityLabel={headingLink.label}
          accessibilityRole="link"
          hitSlop={4}
          onPress={headingLink.onPress}
          style={({ pressed }) => [styles.headingCopy, styles.headingLink, pressed && styles.pressed]}>
          {copy}
        </Pressable>
      ) : <View style={styles.headingCopy}>{copy}</View>}
      {accessory}
    </View>
  );
}

export function EntityCard({
  entity,
  title,
  eyebrow,
  eyebrowAccessory,
  subtitle,
  indicators,
  completion,
  accessory,
  headingLink,
  actions,
  children,
  onPress,
  style,
}: PropsWithChildren<{
  entity: EntityKind;
  title: string;
  eyebrow?: string;
  eyebrowAccessory?: ReactNode;
  subtitle?: string;
  indicators?: StructuralIndicator[];
  completion?: CompletionIndicatorCounts;
  accessory?: ReactNode;
  headingLink?: EntityHeadingLink;
  actions?: ReactNode;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}>) {
  const content = (
    <Card accent={tokens.color[entity]} style={[actions ? styles.entityCardWithActions : null, onPress && styles.entityCardInPressable, style]}>
      <EntityHeading accessory={accessory} completion={completion} entity={entity} eyebrow={eyebrow} eyebrowAccessory={eyebrowAccessory} headingLink={headingLink} indicators={indicators} subtitle={subtitle} title={title} />
      {children}
      {actions ? <EntityCardActions>{actions}</EntityCardActions> : null}
    </Card>
  );
  if (!onPress) return content;
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.entityCardPressable, pressed && styles.pressed]}>
      {content}
    </Pressable>
  );
}

export function EntityCardActions({ children }: PropsWithChildren) {
  return <View accessibilityLabel="Acciones de la card" style={styles.entityCardActions}>{children}</View>;
}

export function EntityCardAction({ children, label, onPress, role = "button" }: PropsWithChildren<{ label: string; onPress(): void; role?: "button" | "link" }>) {
  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole={role}
      hitSlop={8}
      onPress={onPress}
      style={({ pressed }) => [styles.entityCardAction, pressed && styles.pressed]}>
      {children}
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
  const color = tone === "success" ? tokens.color.success : tone === "warning" ? tokens.color.warning : tone === "danger" ? tokens.color.danger : tokens.color.contextual;
  return (
    <View style={[styles.message, { backgroundColor: `${color}1A`, borderColor: `${color}80` }]}>
      <Text style={[styles.messageTitle, { color }]}>{title}</Text>
      <Text style={styles.messageBody}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.72 },
  entityCardPressable: { marginHorizontal: -tokens.spacing.screen },
  entityCardInPressable: { marginHorizontal: 0 },
  entityCardWithActions: { paddingBottom: tokens.card.innerPadding },
  entityCardActions: { alignItems: "center", alignSelf: "stretch", flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "flex-end" },
  entityCardAction: { alignItems: "center", borderRadius: tokens.radius.pill, height: 36, justifyContent: "center", width: 36 },
  headingRow: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md },
  headingCopy: { alignItems: "flex-start", flex: 1, gap: tokens.spacing.xs, minWidth: 0 },
  headingLink: { borderRadius: tokens.radius.md },
  headingEyebrowLine: { alignItems: "center", alignSelf: "stretch", flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "space-between", minWidth: 0 },
  entityEyebrowRow: { alignItems: "center", flexDirection: "row", flexShrink: 1, gap: tokens.spacing.compact, minWidth: 0 },
  headerMetadataChip: { alignItems: "center", backgroundColor: "transparent", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", gap: 4, minHeight: 23, paddingHorizontal: tokens.spacing.sm, paddingVertical: 2 },
  headerMetadataChipText: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.regular, letterSpacing: 0 },
  entityIcon: { alignItems: "center", borderRadius: 5, height: 22, justifyContent: "center", width: 22 },
  entityIconBenefit: { borderRadius: tokens.radius.sm, height: 22, width: 22 },
  entityIconCompact: { height: 18, width: 18 },
  entityIconHeader: { borderRadius: 7, height: 28, width: 28 },
  entityIconHero: { borderRadius: tokens.radius.md, height: 40, width: 40 },
  sectionIcon: { alignItems: "center", backgroundColor: "transparent", height: 22, justifyContent: "center", width: 22 },
  sectionIconCompact: { height: 18, width: 18 },
  sectionIconHero: { height: 40, width: 40 },
  eyebrow: { color: tokens.color.textMuted, flexShrink: 1, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 0, textTransform: "uppercase" },
  headingTitle: { color: tokens.color.textMain, fontSize: tokens.component.entityHeading.card.fontSize, fontWeight: tokens.weight.bold, letterSpacing: 0, lineHeight: tokens.component.entityHeading.card.lineHeight, marginTop: tokens.component.entityHeading.card.marginTop },
  headingSubtitle: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 18 },
  structuralIndicators: { alignItems: "center", alignSelf: "flex-start", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.compact },
  completionIndicators: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.xs },
  completionIndicatorCount: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.semibold },
  completionIndicatorSummary: { alignItems: "center", flexDirection: "row", gap: 3 },
  headingIndicators: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm, marginTop: tokens.component.entityHeading.card.indicatorMarginTop },
  headingIndicatorsPage: { marginTop: tokens.spacing.xs },
  structuralItem: { alignItems: "center", borderRadius: tokens.spacing.compact, flexDirection: "row", gap: tokens.spacing.xs, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  structuralItemSurface: { borderColor: tokens.color.borderDefault, borderWidth: 1 },
  structuralValue: { color: tokens.color.entityIconForeground, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.medium, letterSpacing: 0, lineHeight: 15 },
  structuralValueSurface: { color: tokens.color.textMain },
  guideMetric: { backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.card, justifyContent: "center", minHeight: 58, paddingHorizontal: tokens.spacing.lg, paddingVertical: tokens.spacing.sm },
  guideMetricCopy: { alignItems: "flex-end", gap: 1 },
  guideMetricLabel: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.regular, lineHeight: 12, textAlign: "right" },
  guideMetricValue: { color: tokens.color.textMain, fontSize: 17, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.semibold, lineHeight: 20, textAlign: "right" },
  guideMetricValueOnly: { borderRadius: tokens.radius.lg, minHeight: 40 },
  guideMetricPpk: { backgroundColor: "transparent", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, height: 30, minHeight: 30, paddingHorizontal: tokens.spacing.md, paddingVertical: 0 },
  guideMetricPressed: { opacity: 0.68 },
  guideMetricValuePpk: { color: tokens.color.textMain, fontSize: 15, lineHeight: 18 },
  guideMetricValueRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  entityCardPanelSlot: { minWidth: 0 },
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
  message: { borderRadius: tokens.radius.panel, borderWidth: 1, gap: tokens.spacing.xs, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.card.outerPadding },
  messageTitle: { fontSize: tokens.type.caption, fontWeight: "900", letterSpacing: 0.3 },
  messageBody: { color: tokens.color.textMuted, fontSize: 14, lineHeight: 20 },
});
