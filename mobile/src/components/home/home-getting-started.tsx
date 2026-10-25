import { type Href, useRouter } from "expo-router";
import { CalendarPlus, ClipboardList, Plus, Search, Utensils } from "lucide-react-native";
import type { LucideIcon } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";

import { Button, Card } from "@/components/ui";
import { tokens } from "@/design/tokens";

type GettingStartedCardProps = {
  accent: string;
  description: string;
  icon: LucideIcon;
  primary: { icon: LucideIcon; label: string; onPress(): void };
  secondary: { icon: LucideIcon; label: string; onPress(): void };
  step: number;
  title: string;
};

function GettingStartedCard({ accent, description, icon: Icon, primary, secondary, step, title }: GettingStartedCardProps) {
  const PrimaryIcon = primary.icon;
  const SecondaryIcon = secondary.icon;
  return (
    <Card accent={accent}>
      <View style={styles.cardHeading}>
        <View style={[styles.icon, { backgroundColor: accent }]}>
          <Icon color={tokens.color.entityIconForeground} size={21} strokeWidth={2.2} />
        </View>
        <View style={styles.cardHeadingCopy}>
          <Text style={styles.step}>{`PASO ${step}`}</Text>
          <Text accessibilityRole="header" style={styles.cardTitle}>{title}</Text>
        </View>
      </View>
      <Text style={styles.description}>{description}</Text>
      <View style={styles.actions}>
        <Button icon={<PrimaryIcon color={tokens.color.surfaceApp} size={19} strokeWidth={2.2} />} label={primary.label} onPress={primary.onPress} />
        <Button icon={<SecondaryIcon color={tokens.color.textMain} size={19} strokeWidth={2.2} />} label={secondary.label} onPress={secondary.onPress} variant="secondary" />
      </View>
    </Card>
  );
}

export function HomeGettingStarted({ compactTop = false }: { compactTop?: boolean }) {
  const router = useRouter();
  return (
    <View accessibilityLabel="Primeros pasos" style={[styles.section, compactTop && styles.sectionCompact]}>
      <View style={styles.introduction}>
        <Text accessibilityRole="header" style={styles.title}>Construye tu sistema paso a paso</Text>
        <Text style={styles.subtitle}>Guarda lo que repites, conviértelo en minutas y luego llévalo a tu calendario.</Text>
      </View>
      <GettingStartedCard
        accent={tokens.color.meal}
        description="Guarda las combinaciones que repites para volver a usarlas sin empezar desde cero."
        icon={Utensils}
        primary={{ icon: Search, label: "Explorar comidas", onPress: () => router.push("/explore/meals" as Href) }}
        secondary={{ icon: Plus, label: "Crear desde cero", onPress: () => router.push({ pathname: "/libraries/create", params: { entity: "meal" } }) }}
        step={1}
        title="Agrega comidas recurrentes"
      />
      <GettingStartedCard
        accent={tokens.color.dailyPlan}
        description="Reúne tus comidas en una minuta diaria que puedas reutilizar cuando la necesites."
        icon={ClipboardList}
        primary={{ icon: Search, label: "Explorar minutas", onPress: () => router.push("/explore/daily-plans" as Href) }}
        secondary={{ icon: Plus, label: "Armar con mis comidas", onPress: () => router.push({ pathname: "/libraries/create", params: { entity: "dailyPlan" } }) }}
        step={2}
        title="Define minutas recurrentes"
      />
      <GettingStartedCard
        accent={tokens.color.program}
        description="Lleva una minuta a una fecha concreta o arma una secuencia para varias semanas."
        icon={CalendarPlus}
        primary={{ icon: CalendarPlus, label: "Agregar al calendario", onPress: () => router.push("/calendar" as Href) }}
        secondary={{ icon: Plus, label: "Construir un programa", onPress: () => router.push({ pathname: "/libraries/create", params: { entity: "program" } }) }}
        step={3}
        title="Asigna tus minutas"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  actions: { gap: tokens.spacing.sm, marginTop: tokens.spacing.xs },
  cardHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  cardHeadingCopy: { flex: 1, gap: 2 },
  cardTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.extraBold, lineHeight: 25 },
  description: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  icon: { alignItems: "center", borderRadius: tokens.radius.md, height: 40, justifyContent: "center", width: 40 },
  introduction: { gap: tokens.spacing.xs },
  section: { gap: tokens.spacing.lg, marginTop: tokens.spacing.lg },
  sectionCompact: { marginTop: 0 },
  step: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1 },
  subtitle: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  title: { color: tokens.color.textMain, fontSize: 22, fontWeight: tokens.weight.extraBold, letterSpacing: -0.3 },
});
