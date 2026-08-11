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
      {icon ?? <EntityIcon entity={entity} size="hero" />}
      <View style={styles.copy}>
        <Text style={styles.title}>{title}</Text>
        {count !== undefined ? (
          <StructuralIndicators indicators={[{ icon: countIcon, label: "elementos", value: count }]} />
        ) : null}
      </View>
      {action}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "center", gap: tokens.spacing.md, minWidth: 0, paddingVertical: tokens.spacing.md, width: "100%" },
  copy: { alignItems: "center", gap: tokens.spacing.md, minWidth: 0 },
  title: { color: tokens.color.textMain, fontSize: 22, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 32, textAlign: "center" },
});
