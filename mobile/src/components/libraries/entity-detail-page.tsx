import type { PropsWithChildren } from "react";
import { StyleSheet, Text, View } from "react-native";

import type { LibraryEntity, LibraryIndicator, LibraryNutrition } from "@/api/types";
import { NutritionKpiSection } from "@/components/nutrition/nutrition-kpi-section";
import { Card, SectionTitle } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

import { EntityHeading } from "./entity-card";

export function EntityDetailPage({ children, entity, indicators, nutrition, subtitle, title }: PropsWithChildren<{ entity: LibraryEntity; indicators: LibraryIndicator[]; nutrition: LibraryNutrition; subtitle?: string; title: string }>) {
  return <View style={styles.page}>
    <View style={styles.pageCard}>
      <View style={styles.summary}><EntityHeading entity={entity} indicators={indicators} subtitle={subtitle} title={title} variant="page" /><NutritionKpiSection calories={nutrition.calories} carbs={nutrition.carbs} fat={nutrition.fat} protein={{ ...nutrition.protein, perKilogram: nutrition.protein.per_kilogram }} /></View>
      {children}
    </View>
  </View>;
}

export function EntityDetailSection({ children, detail, title }: PropsWithChildren<{ detail?: string; title: string }>) {
  return <View style={styles.section}><SectionTitle detail={detail} title={title} />{children}</View>;
}

export function EntityDetailMetadata({ createdAt, creator }: { createdAt: string; creator: string }) {
  const date = new Date(createdAt);
  const formatted = Number.isNaN(date.getTime()) ? createdAt : date.toLocaleDateString("es-CL", { day: "numeric", month: "short", year: "numeric" });
  return <Card muted><Text style={styles.metadataTitle}>Información del elemento</Text><View style={styles.metadataRow}><Text style={styles.metadataLabel}>Creado por</Text><Text style={styles.metadataValue}>{creator}</Text></View><View style={styles.metadataRow}><Text style={styles.metadataLabel}>Creado</Text><Text style={styles.metadataValue}>{formatted}</Text></View></Card>;
}

const styles = StyleSheet.create({
  page: { gap: tokens.spacing.lg, minWidth: 0, width: "100%" },
  pageCard: { alignSelf: "stretch", backgroundColor: "transparent", borderWidth: 0, gap: tokens.spacing.lg, minWidth: 0, padding: 0 },
  summary: { gap: tokens.card.gap, minWidth: 0 },
  section: { gap: tokens.spacing.sm, minWidth: 0 },
  metadataTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: "600" },
  metadataRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  metadataLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  metadataValue: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: "500", textAlign: "right" },
});
