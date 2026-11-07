import { ChevronRight, PillBottle } from "lucide-react-native";
import type { PropsWithChildren } from "react";
import { StyleSheet, Text } from "react-native";

import type { SupplementIntakePreset } from "@/api/types";
import { EntityCard, EntityCardAction } from "@/components/ui";
import { tokens } from "@/design/tokens";

export function SupplementIntakePresetCard({ children, contained = false, item, onOpen }: PropsWithChildren<{
  contained?: boolean;
  item: SupplementIntakePreset;
  onOpen?: () => void;
}>) {
  const detailLabel = `Ver detalle de ${item.name}`;
  const summary = item.items.map((row) => String(row.supplement.name ?? "Suplemento guardado")).join(", ");
  return <EntityCard
    accent={tokens.color.supplement}
    actions={onOpen ? <EntityCardAction label={detailLabel} onPress={onOpen} role="link"><ChevronRight color={tokens.color.textMuted} size={19} strokeWidth={2.2} /></EntityCardAction> : undefined}
    entity="supplement"
    eyebrow="Ingesta de suplementos"
    headingLink={onOpen ? { label: detailLabel, onPress: onOpen } : undefined}
    identityIcon={PillBottle}
    indicators={[{ icon: "supplement", label: "sups", value: item.items.length }]}
    style={[styles.card, contained && styles.contained]}
    title={item.name}>
    {summary ? <Text numberOfLines={2} style={styles.summary}>{summary}</Text> : null}
    {children}
  </EntityCard>;
}

const styles = StyleSheet.create({
  card: { marginHorizontal: -18 },
  contained: { marginHorizontal: -18 },
  summary: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 21 },
});
