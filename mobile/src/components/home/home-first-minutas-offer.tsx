import { Sparkles } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/ui";
import { tokens } from "@/design/tokens";

export function HomeFirstMinutasOffer({ onPress }: { onPress(): void }) {
  return <Card accent={tokens.color.dailyPlan} style={styles.card}>
    <View style={styles.heading}>
      <Sparkles color={tokens.color.dailyPlan} size={22} strokeWidth={2.2} />
      <Text style={styles.eyebrow}>PRIMEROS PASOS · INVITACIÓN GRATIS</Text>
    </View>
    <Text accessibilityRole="header" style={styles.title}>Crea 2 minutas según tus objetivos</Text>
    <Text style={styles.subtitle}>Personalízalas con tus preferencias y prográmalas en tu calendario.</Text>
    <Pressable accessibilityLabel="Crear mis 2 minutas gratis" accessibilityRole="button" onPress={onPress} style={styles.action}>
      <Text style={styles.actionLabel}>Crear mis 2 minutas gratis</Text>
    </Pressable>
  </Card>;
}

const styles = StyleSheet.create({
  card: { gap: tokens.spacing.sm },
  heading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  eyebrow: { color: tokens.color.dailyPlan, fontSize: 11, fontWeight: tokens.weight.bold, letterSpacing: 0.8 },
  title: { color: tokens.color.textMain, fontSize: 22, fontWeight: tokens.weight.extraBold, lineHeight: 27 },
  subtitle: { color: tokens.color.textSoft, fontSize: 15, lineHeight: 21 },
  action: { alignItems: "center", alignSelf: "flex-start", backgroundColor: tokens.color.dailyPlan, borderRadius: tokens.radius.pill, marginTop: tokens.spacing.sm, paddingHorizontal: tokens.spacing.lg, paddingVertical: tokens.spacing.sm },
  actionLabel: { color: tokens.color.surfaceApp, fontSize: 14, fontWeight: tokens.weight.bold },
});
