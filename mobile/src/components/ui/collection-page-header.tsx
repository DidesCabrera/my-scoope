import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import {
  EntityIcon,
  type EntityKind,
  SectionIcon,
  type SectionKind,
  StructuralIndicators,
  type StructuralIndicatorKind,
} from "./product";

function PageHeader({ action, icon, indicator, title }: { action?: ReactNode; icon: ReactNode; indicator?: ReactNode; title: string }) {
  return (
    <View style={styles.container}>
      <View style={styles.iconSlot}>{icon}</View>
      <View style={styles.copy}>
        <View style={styles.titleRow}>
          <Text style={styles.title}>{title}</Text>
          {action}
        </View>
        {indicator}
      </View>
    </View>
  );
}

export function CollectionPageHeader({
  action,
  count,
  countIcon,
  entity,
  icon,
  title,
}: {
  action?: ReactNode;
  count?: number;
  countIcon: StructuralIndicatorKind;
  entity: EntityKind;
  icon?: ReactNode;
  title: string;
}) {
  return (
    <PageHeader
      action={action}
      icon={icon ?? <EntityIcon entity={entity} size="hero" />}
      indicator={count !== undefined ? (
          <StructuralIndicators entity={entity} indicators={[{ icon: countIcon, label: "elementos", value: count }]} tone="surfaceMuted" />
      ) : undefined}
      title={title}
    />
  );
}

export function SectionPageHeader({ count, countLabel, section, title }: { count?: number; countLabel: string; section: SectionKind; title: string }) {
  return (
    <PageHeader
      icon={<SectionIcon section={section} size="hero" />}
      indicator={count !== undefined ? (
        <View accessibilityLabel={`${count} ${countLabel}`} accessible style={styles.countChip}>
          <Text style={styles.countValue}>{count}</Text>
          <SectionIcon section={section} size="compact" />
        </View>
      ) : undefined}
      title={title}
    />
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "flex-start", gap: tokens.spacing.sm, minWidth: 0, paddingVertical: tokens.spacing.xs, width: "100%" },
  countChip: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.spacing.compact, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.xs, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  countValue: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.medium, lineHeight: 15 },
  iconSlot: { alignSelf: "flex-start" },
  copy: { alignItems: "flex-start", gap: tokens.spacing.sm, minWidth: 0, width: "100%" },
  titleRow: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", minWidth: 0, width: "100%" },
  title: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.title, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 32, textAlign: "left" },
});
