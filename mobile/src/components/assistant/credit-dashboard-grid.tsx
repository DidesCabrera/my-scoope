import { ChevronRight, Sparkles } from "lucide-react-native";
import { Pressable, StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { tokens } from "@/design/tokens";

type Props = {
  availableCredits: number;
  bleed?: boolean;
  onPress?: () => void;
  planName?: string;
  style?: StyleProp<ViewStyle>;
};

export function CreditDashboardGrid({ availableCredits, bleed, onPress, planName, style }: Props) {
  const usesPanelBleed = bleed ?? !onPress;
  return (
    <Pressable
      accessibilityLabel={onPress ? "Abrir Suscripciones y bolsas" : `${availableCredits} créditos disponibles`}
      accessibilityRole={onPress ? "button" : undefined}
      disabled={!onPress}
      onPress={onPress}
      style={({ pressed }) => [styles.dashboard, usesPanelBleed && styles.panelBleed, style, pressed && styles.pressed]}>
      <Svg aria-hidden height="100%" pointerEvents="none" style={StyleSheet.absoluteFill} width="100%">
        <Defs>
          <LinearGradient id="credit-dashboard-grid-macros" x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Rect fill="url(#credit-dashboard-grid-macros)" height="100%" rx={tokens.radius.panel} ry={tokens.radius.panel} width="100%" />
      </Svg>

      <View style={[styles.grid, !onPress && styles.gridWithoutAction]}>
        {planName ? <View style={[styles.column, styles.planColumn]}>
          <Text style={styles.eyebrow}>Plan</Text>
          <Text numberOfLines={1} style={styles.planName}>{planName}</Text>
        </View> : null}
        <View accessibilityLabel={`${availableCredits} créditos disponibles`} accessible style={[styles.column, styles.creditsColumn]}>
          <View style={styles.creditValueRow}>
            <View style={styles.creditAiIcon}>
              <Sparkles color={tokens.color.surfaceApp} size={16} strokeWidth={2} />
            </View>
            <Text numberOfLines={1} style={styles.creditValue}>{availableCredits.toLocaleString("es-CL")}</Text>
          </View>
          <Text numberOfLines={1} style={styles.creditLabel}>Créditos disponibles</Text>
        </View>
        {onPress ? <View style={[styles.column, styles.actionColumn]}>
          <ChevronRight color={tokens.color.surfaceApp} size={22} strokeWidth={2.4} />
        </View> : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  actionColumn: { alignItems: "center", width: 22 },
  column: { justifyContent: "center", minWidth: 0 },
  creditAiIcon: { alignItems: "center", height: 18, justifyContent: "center", width: 18 },
  creditLabel: { color: tokens.color.surfaceApp, fontSize: 10, fontWeight: tokens.weight.medium, lineHeight: 12 },
  creditsColumn: { alignItems: "flex-end", flex: 10, justifyContent: "flex-end" },
  creditValue: { color: tokens.color.surfaceApp, fontSize: 18, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, lineHeight: 21 },
  creditValueRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  dashboard: { borderRadius: tokens.radius.panel, minHeight: 70, overflow: "hidden" },
  eyebrow: { color: tokens.color.surfaceApp, fontSize: 9, fontWeight: tokens.weight.bold, letterSpacing: 0.8, lineHeight: 11, opacity: 0.72, textTransform: "uppercase", transform: [{ translateX: 1 }] },
  grid: { flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 70, paddingLeft: tokens.spacing.lg, paddingRight: tokens.spacing.xs, paddingVertical: tokens.spacing.md },
  gridWithoutAction: { paddingRight: tokens.spacing.lg },
  panelBleed: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  planColumn: { alignItems: "flex-start", flex: 13, justifyContent: "flex-start" },
  planName: { color: tokens.color.surfaceApp, fontSize: 24, fontWeight: tokens.weight.bold, lineHeight: 28 },
  pressed: { opacity: 0.72 },
});
