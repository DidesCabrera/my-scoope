import { ChevronLeft } from "lucide-react-native";
import type { PropsWithChildren, ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import {
  type NutritionEntityCardProps,
  NutritionKpiSection,
} from "@/components/nutrition";
import { ContentPanel, EntityHeading, SectionHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";

export type EntityDetailPageProps = PropsWithChildren<
  Omit<NutritionEntityCardProps, "children" | "onPress" | "style"> & {
    action?: ReactNode;
    backLabel?: string;
    onBack?: () => void;
    showNutrition?: boolean;
  }
>;

export function EntityDetailPage({
  action,
  backLabel = "Volver",
  children,
  accessory,
  completion,
  kpiVariant = "regular",
  entity,
  eyebrow,
  indicators,
  nutrition,
  onBack,
  showNutrition = true,
  subtitle,
  title,
}: EntityDetailPageProps) {
  return (
    <View style={styles.page}>
      {onBack || action ? (
        <View style={styles.navigation}>
          {onBack ? (
            <Pressable
              accessibilityLabel={backLabel}
              accessibilityRole="button"
              hitSlop={8}
              onPress={onBack}
              style={({ pressed }) => [styles.backButton, pressed && styles.pressed]}>
              <ChevronLeft color={tokens.color.textMain} size={18} strokeWidth={2.3} />
              <Text style={styles.backLabel}>{backLabel}</Text>
            </Pressable>
          ) : <View />}
          {action}
        </View>
      ) : null}

      <View style={styles.pageCard}>
        <View style={styles.summary}>
          <EntityHeading
            accessory={accessory}
            completion={completion}
            entity={entity}
            eyebrow={eyebrow}
            indicators={indicators}
            subtitle={subtitle}
            title={title}
            variant="page"
          />
          {showNutrition ? <NutritionKpiSection variant={kpiVariant} {...nutrition} /> : null}
        </View>
        {children}
      </View>
    </View>
  );
}

export function EntityDetailSection({
  children,
  detail,
  title,
}: PropsWithChildren<{ detail?: string; title: string }>) {
  return (
    <View style={styles.section}>
      <SectionHeading detail={detail} title={title} />
      {children}
    </View>
  );
}

export function EntityDetailMetadata({
  creator,
  updatedAt,
}: {
  creator: string;
  updatedAt?: string;
}) {
  return (
    <ContentPanel muted title="Información del elemento">
      <View style={styles.metadataRow}>
        <Text style={styles.metadataLabel}>Creado por</Text>
        <Text style={styles.metadataValue}>{creator}</Text>
      </View>
      {updatedAt ? (
        <View style={styles.metadataRow}>
          <Text style={styles.metadataLabel}>Actualizado</Text>
          <Text style={styles.metadataValue}>{updatedAt}</Text>
        </View>
      ) : null}
    </ContentPanel>
  );
}

const styles = StyleSheet.create({
  page: { gap: tokens.spacing.lg, minWidth: 0, width: "100%" },
  pageCard: { alignSelf: "stretch", gap: tokens.spacing.lg, marginHorizontal: -tokens.spacing.screen, minWidth: 0, paddingBottom: tokens.card.outerPadding, paddingHorizontal: tokens.card.outerPadding },
  summary: { gap: tokens.card.gap, minWidth: 0 },
  navigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", minHeight: 32 },
  backButton: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs, minHeight: 32 },
  backLabel: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, letterSpacing: 0 },
  pressed: { opacity: 0.65 },
  section: { gap: tokens.spacing.sm, minWidth: 0 },
  metadataRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  metadataLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0 },
  metadataValue: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, letterSpacing: 0, textAlign: "right" },
});
