import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import {
  EntityIcon,
  type EntityKind,
  StructuralIndicators,
  type StructuralIndicatorKind,
} from "./product";

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
    <View style={styles.container}>
      <View style={styles.iconSlot}>
        {icon ?? <EntityIcon entity={entity} size="hero" />}
      </View>
      <View style={styles.copy}>
        <View style={styles.titleRow}>
          <Text style={styles.title}>{title}</Text>
          {action}
        </View>
        {count !== undefined ? (
          <StructuralIndicators entity={entity} indicators={[{ icon: countIcon, label: "elementos", value: count }]} tone="surfaceMuted" />
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, minWidth: 0, paddingVertical: tokens.spacing.xs, width: "100%" },
  iconSlot: { paddingTop: tokens.spacing.xs },
  copy: { alignItems: "flex-start", flex: 1, gap: tokens.spacing.sm, minWidth: 0 },
  titleRow: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", minWidth: 0, width: "100%" },
  title: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.title, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 32, textAlign: "left" },
});
