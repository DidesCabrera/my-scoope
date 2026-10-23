import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { PRODUCT_VOCABULARY_ES } from "@/copy/product-vocabulary";
import { tokens } from "@/design/tokens";
import {
  EntityIcon,
  type EntityKind,
  SectionIcon,
  type SectionKind,
} from "./product";
import { Chip } from "./chip";

const collectionCountLabels: Record<EntityKind, { plural: string; singular: string }> = {
  comparison: { plural: "Comparaciones", singular: "Comparación" },
  dailyPlan: PRODUCT_VOCABULARY_ES.dailyPlan,
  dpm: PRODUCT_VOCABULARY_ES.dailyPlan,
  food: { plural: "Alimentos", singular: "Alimento" },
  meal: { plural: "Comidas", singular: "Comida" },
  program: { plural: "Programas semanales", singular: "Programa semanal" },
};

function PageHeader({ action, icon, indicator, subtitle, title }: { action?: ReactNode; icon: ReactNode; indicator?: ReactNode; subtitle?: string; title: string }) {
  return (
    <View style={styles.container}>
      <View style={styles.iconSlot}>{icon}</View>
      <View style={styles.copy}>
        <View style={styles.titleRow}>
          <Text style={styles.title}>{title}</Text>
          {action}
        </View>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        {indicator}
      </View>
    </View>
  );
}

export function CollectionPageHeader({
  action,
  count,
  entity,
  icon,
  title,
}: {
  action?: ReactNode;
  count?: number;
  entity: EntityKind;
  icon?: ReactNode;
  title: string;
}) {
  return (
    <PageHeader
      action={action}
      icon={icon ?? <EntityIcon entity={entity} size="hero" />}
      indicator={count !== undefined ? (
        <Chip
          backgroundColor={`${tokens.color[entity]}1A`}
          borderColor={tokens.color[entity]}
          label={`${count} ${collectionCountLabels[entity][count === 1 ? "singular" : "plural"]}`}
          textColor={tokens.color.textMain}
        />
      ) : undefined}
      title={title}
    />
  );
}

export function SectionPageHeader({ count, countLabel, icon, indicator, section, subtitle, title }: { count?: number; countLabel?: string; icon?: ReactNode; indicator?: ReactNode; section: SectionKind; subtitle?: string; title: string }) {
  return (
    <PageHeader
      icon={icon ?? <SectionIcon section={section} size="hero" />}
      indicator={indicator ?? (count !== undefined ? (
        <View accessibilityLabel={`${count} ${countLabel}`} accessible style={styles.countChip}>
          <Text style={styles.countValue}>{count}</Text>
          <SectionIcon section={section} size="compact" />
        </View>
      ) : undefined)}
      subtitle={subtitle}
      title={title}
    />
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "flex-start", gap: tokens.spacing.sm, minWidth: 0, paddingVertical: tokens.spacing.xs, width: "100%" },
  countChip: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.spacing.compact, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.xs, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  countValue: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.medium, lineHeight: 15 },
  iconSlot: { alignSelf: "flex-start" },
  subtitle: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  copy: { alignItems: "flex-start", gap: tokens.spacing.sm, minWidth: 0, width: "100%" },
  titleRow: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", minWidth: 0, width: "100%" },
  title: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.title, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 32, textAlign: "left" },
});
