import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Defs, G, LinearGradient, Mask, Path, Rect, Stop } from "react-native-svg";

import { Card } from "@/components/ui";
import { tokens } from "@/design/tokens";

function OfferAssistantIcon() {
  return <View style={styles.assistantIcon}>
    <Svg aria-hidden height={27} viewBox="0 0 27 27" width={27}>
      <Defs>
        <Mask id="home-first-minutas-assistant-cutout" maskType="luminance">
          <Rect fill="#fff" height={27} width={27} />
          <G transform="translate(4.86 4.86) scale(0.72)">
            <Path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z" fill="none" stroke="#000" strokeLinejoin="round" strokeWidth={2.2} />
            <Path d="M20 2v4M22 4h-4" fill="none" stroke="#000" strokeLinecap="round" strokeWidth={2.2} />
            <Circle cx={4} cy={20} fill="none" r={2} stroke="#000" strokeWidth={2.2} />
          </G>
        </Mask>
      </Defs>
      <Rect fill={tokens.color.surfaceApp} height={27} mask="url(#home-first-minutas-assistant-cutout)" rx={tokens.radius.sm} width={27} />
    </Svg>
  </View>;
}

export function HomeFirstMinutasOffer({ onPress }: { onPress(): void }) {
  return <Card style={styles.card}>
    <Svg aria-hidden height="100%" pointerEvents="none" style={StyleSheet.absoluteFill} width="100%">
      <Defs>
        <LinearGradient id="home-first-minutas-offer-macros" x1="0" x2="1" y1="0" y2="1">
          <Stop offset="0" stopColor={tokens.color.protein} />
          <Stop offset="0.5" stopColor={tokens.color.carbs} />
          <Stop offset="1" stopColor={tokens.color.fat} />
        </LinearGradient>
      </Defs>
      <Rect fill="url(#home-first-minutas-offer-macros)" height="100%" width="100%" />
    </Svg>
    <View style={styles.content}>
      <View style={styles.heading}>
        <OfferAssistantIcon />
        <Text style={styles.eyebrow}>PRIMEROS PASOS · INVITACIÓN GRATIS</Text>
      </View>
      <Text accessibilityRole="header" style={styles.title}>Crea 2 minutas según tus objetivos</Text>
      <Text style={styles.subtitle}>Prueba nuestro <Text style={styles.subtitleEmphasis}>asistente nutricional</Text> creando tus primeras dos minutas. Posteriormente podrás <Text style={styles.subtitleEmphasis}>ajustarlas y calendarizarlas</Text>, para que comiences tu proceso</Text>
      <Image accessible={false} resizeMode="contain" source={require("../../../assets/images/home-food-formats-composite-v4-small.png")} style={styles.illustration} />
      <Pressable accessibilityLabel="Crear mis 2 minutas gratis" accessibilityRole="button" onPress={onPress} style={styles.action}>
        <Text style={styles.actionLabel}>Crear mis 2 minutas gratis</Text>
      </Pressable>
    </View>
  </Card>;
}

const styles = StyleSheet.create({
  assistantIcon: { alignItems: "center", borderRadius: tokens.radius.sm, height: 27, justifyContent: "center", width: 27 },
  card: { backgroundColor: "transparent", borderWidth: 0, gap: 0, overflow: "hidden", padding: 0 },
  content: { gap: tokens.spacing.sm, padding: tokens.card.outerPadding },
  heading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  eyebrow: { color: tokens.color.surfaceApp, fontSize: 11, fontWeight: tokens.weight.bold, letterSpacing: 0.8 },
  title: { color: tokens.color.surfaceApp, fontSize: 22, fontWeight: tokens.weight.extraBold, lineHeight: 27 },
  subtitle: { color: tokens.color.surfaceApp, fontSize: 15, lineHeight: 21 },
  subtitleEmphasis: { fontWeight: tokens.weight.bold },
  illustration: { alignSelf: "center", height: 180, marginTop: 10, maxWidth: 384, transform: [{ translateX: -4 }], width: "100%" },
  action: { alignItems: "center", alignSelf: "flex-end", backgroundColor: "transparent", borderColor: tokens.color.surfaceApp, borderRadius: tokens.radius.pill, borderWidth: 1.5, justifyContent: "center", marginTop: tokens.spacing.sm, minHeight: 44, paddingHorizontal: tokens.spacing.lg, paddingVertical: tokens.spacing.sm },
  actionLabel: { color: tokens.color.surfaceApp, fontSize: 14, fontWeight: tokens.weight.bold },
});
