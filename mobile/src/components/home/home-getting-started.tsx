import { useState } from "react";
import { type Href, useRouter } from "expo-router";
import { ClipboardList, LibraryBig, Plus, Search, Utensils } from "lucide-react-native";
import type { LucideIcon } from "lucide-react-native";
import { Image, type ImageSourcePropType, type ImageStyle, Pressable, type StyleProp, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

type GettingStartedCardProps = {
  accent: string;
  eyebrow: string;
  gradientSource: ImageSourcePropType;
  icon: LucideIcon;
  imageSource: ImageSourcePropType;
  imageStyle?: StyleProp<ImageStyle>;
  primary: { icon: LucideIcon; label: string; onPress(): void };
  secondary: { icon: LucideIcon; label: string; onPress(): void };
  title: string;
};

function GettingStartedCard({ accent, eyebrow, gradientSource, icon: Icon, imageSource, imageStyle, primary, secondary, title }: GettingStartedCardProps) {
  const [cardSize, setCardSize] = useState({ width: 0, height: 0 });
  return (
    <View onLayout={({ nativeEvent: { layout } }) => {
      if (layout.width !== cardSize.width || layout.height !== cardSize.height) setCardSize({ width: layout.width, height: layout.height });
    }} style={styles.card}>
      <Image accessible={false} resizeMode="stretch" source={gradientSource} style={[styles.gradient, cardSize]} />
      <View style={styles.cardHeading}>
        <View style={[styles.icon, { backgroundColor: accent }]}>
          <Icon color={tokens.color.entityIconForeground} size={21} strokeWidth={2.2} />
        </View>
        <View style={styles.cardHeadingCopy}>
          <Text style={styles.eyebrow}>{eyebrow}</Text>
          <Text accessibilityRole="header" style={styles.cardTitle}>{title}</Text>
        </View>
      </View>
      <View style={styles.cardBody}>
        <View style={styles.imageArea}>
          <Image accessible={false} resizeMode="contain" source={imageSource} style={[styles.illustration, imageStyle]} />
        </View>
        <View style={styles.actions}>
          {[primary, secondary].map(({ icon: ActionIcon, label, onPress }) => (
            <Pressable accessibilityLabel={label} accessibilityRole="button" hitSlop={6} key={label} onPress={onPress} style={({ pressed }) => [styles.action, { borderColor: accent }, pressed && styles.actionPressed]}>
              <ActionIcon color={tokens.color.entityIconForeground} size={16} strokeWidth={2.2} />
              <Text style={styles.actionLabel}>{label}</Text>
            </Pressable>
          ))}
        </View>
      </View>
    </View>
  );
}

export function HomeGettingStarted({ compactTop = false }: { compactTop?: boolean }) {
  const router = useRouter();
  return (
    <View accessibilityLabel="Primeros pasos" style={[styles.section, compactTop && styles.sectionCompact]}>
      <View style={styles.introduction}>
        <View style={styles.introductionHeading}>
          <LibraryBig color={tokens.color.textMain} size={25} strokeWidth={2.2} />
          <Text accessibilityRole="header" style={styles.title}>Enriquece tus librerías</Text>
        </View>
      </View>
      <GettingStartedCard
        accent={tokens.color.meal}
        eyebrow="Mi librería de comidas"
        gradientSource={require("../../../assets/images/home-meals-gradient-25-17.png")}
        icon={Utensils}
        imageSource={require("../../../assets/images/home-meals-bowl.png")}
        imageStyle={styles.mealIllustration}
        primary={{ icon: Search, label: "Explorar comidas", onPress: () => router.push("/explore/meals" as Href) }}
        secondary={{ icon: Plus, label: "Crear desde cero", onPress: () => router.push({ pathname: "/libraries/create", params: { entity: "meal" } }) }}
        title="Agrega comidas recurrentes"
      />
      <GettingStartedCard
        accent={tokens.color.dailyPlan}
        eyebrow="Mi librería de minutas"
        gradientSource={require("../../../assets/images/home-daily-plans-gradient-25-17.png")}
        icon={ClipboardList}
        imageSource={require("../../../assets/images/home-daily-plans-containers.png")}
        imageStyle={styles.dailyPlanIllustration}
        primary={{ icon: Search, label: "Explorar minutas", onPress: () => router.push("/explore/daily-plans" as Href) }}
        secondary={{ icon: Plus, label: "Armar con mis comidas", onPress: () => router.push({ pathname: "/libraries/create", params: { entity: "dailyPlan" } }) }}
        title="Define minutas reutilizables"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: tokens.color.surfaceApp, borderRadius: tokens.radius.card, gap: tokens.card.gap, marginHorizontal: -tokens.spacing.screen, overflow: "hidden", padding: tokens.card.outerPadding },
  gradient: { left: 0, position: "absolute", top: 0 },
  action: { alignItems: "center", alignSelf: "flex-end", borderRadius: 999, borderWidth: 1, flexDirection: "row", gap: 6, justifyContent: "center", minHeight: 34, paddingHorizontal: 12 },
  actionLabel: { color: tokens.color.entityIconForeground, fontSize: 13, fontWeight: "700" },
  actionPressed: { opacity: 0.72 },
  actions: { alignItems: "flex-end", gap: tokens.spacing.sm },
  cardBody: { alignItems: "flex-end", flexDirection: "row", gap: tokens.spacing.xs, marginTop: 18 },
  cardHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  cardHeadingCopy: { flex: 1, gap: 2 },
  cardTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.extraBold, lineHeight: 25 },
  dailyPlanIllustration: { transform: [{ scale: 1.15 }, { translateX: -2 }, { translateY: -4 }] },
  icon: { alignItems: "center", borderRadius: tokens.radius.md, height: 40, justifyContent: "center", width: 40 },
  illustration: { height: 100, width: "100%" },
  imageArea: { flex: 1, minWidth: 0 },
  mealIllustration: { transform: [{ translateX: -18 }, { translateY: -4 }] },
  introduction: { marginTop: 28 },
  introductionHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  section: { gap: tokens.spacing.lg, marginTop: tokens.spacing.lg },
  sectionCompact: { marginTop: 0 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1 },
  title: { color: tokens.color.textMain, fontSize: 22, fontWeight: tokens.weight.extraBold, letterSpacing: -0.3 },
});
