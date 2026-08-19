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
      <View style={styles.identity}>
        {icon ?? <EntityIcon entity={entity} size="hero" />}
        <Text style={styles.title}>{title}</Text>
      </View>
      {count !== undefined ? (
        <StructuralIndicators indicators={[{ icon: countIcon, label: "elementos", value: count }]} />
      ) : null}
      {action}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "flex-start", gap: tokens.spacing.md, minWidth: 0, paddingVertical: tokens.spacing.md, width: "100%" },
  identity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, minWidth: 0, width: "100%" },
  title: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.title, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 32, textAlign: "left" },
});
