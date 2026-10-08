import { Activity, HeartPulse, IdCard, Scale } from "lucide-react-native";
import type { ComponentType, ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Button, Card } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

export type PersonalRecordKind = "body" | "planning" | "preferences" | "metrics";

export type PersonalRecordItem = {
  isPending?: boolean;
  key: string;
  label: string;
  value: string;
};

const variants: Record<PersonalRecordKind, {
  accent: string;
  description: string;
  eyebrow: string;
  icon: ComponentType<{ color: string; size: number }>;
  title: string;
}> = {
  body: {
    accent: tokens.color.interactivePrimary,
    description: "Datos estables usados para estimar necesidades energéticas y nutricionales.",
    eyebrow: "Base de cálculo",
    icon: IdCard,
    title: "Ficha corporal",
  },
  planning: {
    accent: tokens.color.dailyPlan,
    description: "Contexto persistente que orienta objetivos, planes y programas.",
    eyebrow: "Planificación",
    icon: Activity,
    title: "Objetivo y actividad",
  },
  preferences: {
    accent: tokens.color.meal,
    description: "Patrón alimentario, alergias y alimentos evitados aprobados por ti.",
    eyebrow: "Alimentación",
    icon: HeartPulse,
    title: "Preferencias alimentarias",
  },
  metrics: {
    accent: tokens.color.program,
    description: "Última medición disponible, conservando el historial corporal.",
    eyebrow: "Seguimiento",
    icon: Scale,
    title: "Métricas corporales",
  },
};

export function PersonalRecordCard({
  action,
  description,
  items,
  kind,
  title,
}: {
  action?: ReactNode;
  description?: string;
  items: PersonalRecordItem[];
  kind: PersonalRecordKind;
  title?: string;
}) {
  const variant = variants[kind];
  const Icon = variant.icon;
  return (
    <Card accent={variant.accent} style={styles.card}>
      <View style={styles.heading}>
        <View style={[styles.icon, { borderColor: variant.accent }]}>
          <Icon color={tokens.color.textMain} size={20} />
        </View>
        <View style={styles.headingCopy}>
          <Text style={styles.eyebrow}>{variant.eyebrow}</Text>
          <Text style={styles.title}>{title || variant.title}</Text>
        </View>
      </View>
      <Text style={styles.description}>{description || variant.description}</Text>
      <View style={styles.items}>
        {items.map((item) => (
          <View key={item.key} style={styles.item}>
            <Text style={styles.itemLabel}>{item.label}</Text>
            <Text style={[styles.itemValue, item.isPending && styles.pending]}>{item.value}</Text>
          </View>
        ))}
      </View>
      {action ? <View style={styles.action}>{action}</View> : null}
    </Card>
  );
}

export function PersonalRecordCardAction({ label, onPress }: { label: string; onPress(): void }) {
  return <Button label={label} onPress={onPress} variant="secondary" />;
}

const styles = StyleSheet.create({
  action: { marginTop: tokens.spacing.xs },
  card: { gap: tokens.spacing.md },
  description: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, textTransform: "uppercase" },
  heading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  headingCopy: { flex: 1, gap: 2 },
  icon: { alignItems: "center", borderRadius: tokens.radius.md, borderWidth: 1, height: 40, justifyContent: "center", width: 40 },
  item: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, gap: 2, paddingTop: tokens.spacing.sm },
  itemLabel: { color: tokens.color.textSoft, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  itemValue: { color: tokens.color.textMain, fontSize: tokens.type.body },
  items: { gap: tokens.spacing.sm },
  pending: { color: tokens.color.textMuted },
  title: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
});
