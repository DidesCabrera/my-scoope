import { StyleSheet, Text, View } from "react-native";

import { ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button } from "@/components/ui/controls";
import { ProgressBar } from "@/components/ui/feedback";
import { MyScoopeBrandLogo } from "@/components/ui/my-scoope-brand-logo";
import { EntityIcon } from "@/components/ui/product";
import { Card } from "@/components/ui/surfaces";
import { textStyles } from "@/components/ui/typography";
import { tokens } from "@/design/tokens";

import type { CommercialLimitEntity, CommercialLimitState } from "./commercial-limit";

export type { CommercialLimitEntity, CommercialLimitState } from "./commercial-limit";

const content = {
  comparison: { noun: "comparaciones", title: "Guarda comparaciones en tu librería", usageLabel: "Comparaciones guardadas" },
  dailyPlan: { noun: "minutas diarias", title: "Agrega más minutas a tu librería", usageLabel: "Minutas utilizadas" },
  meal: { noun: "comidas", title: "Agrega más comidas a tu librería", usageLabel: "Comidas utilizadas" },
  program: { noun: "programas", title: "Agrega más programas a tu librería", usageLabel: "Programas utilizados" },
} satisfies Record<CommercialLimitEntity, { noun: string; title: string; usageLabel: string }>;

function limitDescription(entity: CommercialLimitEntity, limit: number) {
  if (entity === "comparison" && limit === 0) return "Tu plan actual no incluye comparaciones guardadas.";
  if (entity === "comparison") return `Ya guardaste las ${limit} comparaciones incluidas en tu plan.`;
  if (entity === "meal") return `Ya usaste las ${limit} comidas incluidas en tu plan.`;
  if (entity === "program" && limit === 1) return "Ya usaste el programa incluido en tu plan.";
  return `Ya usaste los ${limit} ${content[entity].noun} incluidos en tu plan.`;
}

type CommercialLimitContentProps = CommercialLimitState & {
  onClose(): void;
  onUpgrade(): void;
};

export function CommercialLimitContent({ entity, limit, onClose, onUpgrade, planName, used }: CommercialLimitContentProps) {
  const copy = content[entity];
  const accent = tokens.color[entity];
  return (
    <Card accent={tokens.color.carbs} style={styles.card}>
      <View style={styles.copy}>
        <View style={styles.brandLogo}><MyScoopeBrandLogo commercial /></View>
        <Text style={styles.eyebrow}>LÍMITE DEL PLAN {planName.toUpperCase()}</Text>
        <Text style={styles.title}>{copy.title}</Text>
        <Text style={[textStyles.muted, styles.subtitle]}>{limitDescription(entity, limit)} Tu contenido actual sigue disponible.</Text>
      </View>
      <View style={[styles.usagePanel, { borderTopColor: accent }]}>
        <View style={styles.usageHeader}>
          <View style={styles.usageIdentity}>
            <EntityIcon entity={entity} size="regular" />
            <Text style={styles.usageLabel}>{copy.usageLabel}</Text>
          </View>
          <Text style={styles.usageValue}>{used} de {limit}</Text>
        </View>
        <View style={styles.progressSpacing}>
          <ProgressBar color={accent} value={limit > 0 ? Math.min(100, (used / limit) * 100) : 100} />
        </View>
        <Text style={styles.usageDisclaimer}>Planes Basic y Pro ilimitados</Text>
      </View>
      <Text style={styles.planBenefitsCopy}>
        Conoce todos los beneficios de nuestros planes <Text style={styles.planNameEmphasis}>Basic</Text> y <Text style={styles.planNameEmphasis}>Pro</Text>
      </Text>
      <View style={styles.actions}>
        <Button label="Ver planes disponibles" onPress={onUpgrade} variant="gradient" />
        <Button label="Seguir con mi contenido" onPress={onClose} variant="secondary" />
      </View>
    </Card>
  );
}

export function CommercialLimitSheet({ entity, limit, onClose, onUpgrade, planName, used, visible }: CommercialLimitContentProps & { visible: boolean }) {
  return (
    <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <View style={styles.sheetContent}>
        <CommercialLimitContent entity={entity} limit={limit} onClose={onClose} onUpgrade={onUpgrade} planName={planName} used={used} />
      </View>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  actions: { gap: tokens.spacing.sm },
  brandLogo: { alignItems: "center", marginBottom: 6 },
  card: { marginHorizontal: 0 },
  copy: { alignItems: "center", gap: tokens.spacing.sm },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1, textAlign: "center" },
  planBenefitsCopy: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold, lineHeight: 23, textAlign: "center" },
  planNameEmphasis: { fontWeight: tokens.weight.extraBold },
  progressSpacing: { marginBottom: 8, marginTop: 8 },
  sheetContent: { paddingBottom: tokens.spacing.md, paddingHorizontal: tokens.spacing.screen },
  subtitle: { textAlign: "center" },
  title: { color: tokens.color.textMain, fontSize: tokens.type.title, fontWeight: tokens.weight.extraBold, lineHeight: 32, textAlign: "center" },
  usageHeader: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "space-between", marginTop: 4 },
  usageIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm },
  usageDisclaimer: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold, textAlign: "center" },
  usageLabel: { color: tokens.color.textMain, flex: 1, fontSize: 18, fontWeight: tokens.weight.bold },
  usagePanel: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderTopWidth: 3, borderWidth: 1, gap: tokens.spacing.sm, marginHorizontal: -6, overflow: "hidden", padding: tokens.spacing.md },
  usageValue: { color: tokens.color.textMain, fontSize: 18, fontWeight: tokens.weight.extraBold },
});
