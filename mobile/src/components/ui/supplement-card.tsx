import { ChevronRight } from "lucide-react-native";
import type { PropsWithChildren } from "react";
import { StyleSheet, View } from "react-native";

import { tokens } from "@/design/tokens";
import { Chip } from "./chip";
import { EntityCard, EntityCardAction } from "./product";

const unitLabels: Record<string, { plural?: string; singular: string }> = {
  capsule: { plural: "cápsulas", singular: "cápsula" },
  drop: { plural: "gotas", singular: "gota" },
  g: { singular: "g" },
  gummy: { plural: "gomitas", singular: "gomita" },
  iu: { singular: "UI" },
  mcg: { singular: "mcg" },
  mg: { singular: "mg" },
  ml: { singular: "ml" },
  sachet: { plural: "sobres", singular: "sobre" },
  scoop: { plural: "medidas", singular: "medida" },
  softgel: { plural: "cápsulas blandas", singular: "cápsula blanda" },
  tablet: { plural: "comprimidos", singular: "comprimido" },
  tsp: { plural: "cucharaditas", singular: "cucharadita" },
};

function doseLabel(quantityValue?: string | null, unitValue?: string | null) {
  if (!quantityValue || !unitValue) return null;
  const quantity = Number(quantityValue);
  const formatted = Number.isFinite(quantity)
    ? quantity.toLocaleString("es-CL", { maximumFractionDigits: 3 })
    : quantityValue;
  const labels = unitLabels[unitValue];
  const unit = labels ? quantity === 1 ? labels.singular : labels.plural ?? labels.singular : unitValue;
  return `${formatted} ${unit}`;
}

export function SupplementCard({
  brand,
  children,
  componentCount = 0,
  contained = false,
  name,
  onOpen,
  quantity,
  unit,
}: PropsWithChildren<{
  brand?: string | null;
  componentCount?: number;
  contained?: boolean;
  name: string;
  onOpen?: () => void;
  quantity?: string | null;
  unit?: string | null;
}>) {
  const metadata = [
    doseLabel(quantity, unit),
    componentCount ? `${componentCount} ${componentCount === 1 ? "componente" : "componentes"}` : null,
  ].filter((value): value is string => Boolean(value));
  const detailLabel = `Ver detalle de ${name}`;
  return (
    <EntityCard
      accent={tokens.color.supplement}
      actions={onOpen ? <EntityCardAction label={detailLabel} onPress={onOpen} role="link"><ChevronRight color={tokens.color.textMuted} size={19} strokeWidth={2.2} /></EntityCardAction> : undefined}
      entity="supplement"
      eyebrow="Suplemento"
      headingLink={onOpen ? { label: detailLabel, onPress: onOpen } : undefined}
      style={[styles.card, contained && styles.contained]}
      subtitle={brand || undefined}
      title={name}>
      {metadata.length ? <View style={styles.metadata}>{metadata.map((label) => <Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} key={label} label={label} textColor={tokens.color.textMain} />)}</View> : null}
      {children}
    </EntityCard>
  );
}

const styles = StyleSheet.create({
  card: { marginHorizontal: -18 },
  contained: { marginHorizontal: -18 },
  metadata: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
});
