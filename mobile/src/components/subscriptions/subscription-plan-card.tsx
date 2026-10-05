import { Check, Inbox, type LucideIcon, Scale, Sparkles } from "lucide-react-native";
import type { ReactNode } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { Card, EntityIcon, type EntityKind, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";

type PlanBenefit = { entity?: EntityKind; icon?: LucideIcon; label: string; value: string };

export const commercialPlanBenefits: Record<"Basic" | "Free" | "Pro", PlanBenefit[]> = {
  Free: [
    { entity: "food", label: "Alimentos privados", value: "Ilimitados" },
    { entity: "meal", label: "Comidas", value: "Hasta 12" },
    { entity: "dailyPlan", label: "Planes diarios", value: "Hasta 4" },
    { entity: "program", label: "Programas", value: "1 de hasta 2 semanas" },
    { icon: Inbox, label: "Compartidos", value: "1 incorporación al mes" },
    { icon: Scale, label: "Comparaciones", value: "Sin guardadas" },
    { icon: Sparkles, label: "Asistencia IA", value: "Sin créditos incluidos" },
  ],
  Basic: [
    { entity: "food", label: "Alimentos", value: "Ilimitados" },
    { entity: "meal", label: "Comidas", value: "Ilimitadas" },
    { entity: "dailyPlan", label: "Planes diarios", value: "Ilimitados" },
    { entity: "program", label: "Programas", value: "Ilimitados · hasta 12 semanas" },
    { icon: Inbox, label: "Compartidos", value: "Incorporaciones ilimitadas" },
    { icon: Scale, label: "Comparaciones", value: "Ilimitadas" },
    { icon: Sparkles, label: "Asistencia IA", value: "150 créditos al mes" },
  ],
  Pro: [
    { icon: Check, label: "Incluye", value: "Todo lo de Basic" },
    { icon: Sparkles, label: "Asistencia IA", value: "1.000 créditos al mes" },
  ],
};

export function SubscriptionPlanCard({ accent, benefits, caption, children, name, price }: {
  accent: string;
  benefits: PlanBenefit[];
  caption?: string;
  children?: ReactNode;
  name: string;
  price: string;
}) {
  return (
    <Card accent={accent}>
      <View style={styles.copy}>
        <Text style={styles.eyebrow}>PLAN DE SUSCRIPCIÓN</Text>
        <View style={styles.productTitleRow}>
          <Text style={styles.productName}>{name}</Text>
          <View style={[styles.planPriceChip, { backgroundColor: accent }]}>
            <Text numberOfLines={1} style={styles.planPriceChipLabel}>{price}</Text>
          </View>
        </View>
        {caption ? <Text style={textStyles.caption}>{caption}</Text> : null}
      </View>
      <View style={styles.benefitRows}>
        {benefits.map((item, index) => {
          const Icon = item.icon;
          return (
            <View key={item.label} style={[styles.benefitRow, index === benefits.length - 1 && styles.benefitRowLast]}>
              <View style={styles.benefitIdentity}>
                {item.entity ? <EntityIcon entity={item.entity} size="benefit" /> : Icon ? <View style={styles.benefitIcon}><Icon color={tokens.color.textMain} size={14} strokeWidth={2.2} /></View> : null}
                <Text style={styles.benefitLabel}>{item.label}</Text>
              </View>
              <Text adjustsFontSizeToFit minimumFontScale={0.72} numberOfLines={1} style={styles.benefitValue}>{item.value}</Text>
            </View>
          );
        })}
      </View>
      {children}
    </Card>
  );
}

export function SubscriptionPurchaseButton({ disabled = false, label, loading = false, onPress }: {
  disabled?: boolean;
  label: string;
  loading?: boolean;
  onPress(): void;
}) {
  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="button"
      accessibilityState={{ busy: loading, disabled: disabled || loading }}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [styles.purchaseButton, (disabled || loading) && styles.purchaseButtonDisabled, pressed && styles.purchaseButtonPressed]}>
      <Svg aria-hidden pointerEvents="none" style={StyleSheet.absoluteFill}>
        <Defs>
          <LinearGradient id="subscription-purchase-macros" x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Rect fill="url(#subscription-purchase-macros)" height="100%" width="100%" />
      </Svg>
      {loading ? <ActivityIndicator color={tokens.color.surfaceApp} /> : null}
      <Text style={styles.purchaseButtonLabel}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  benefitIcon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.sm, height: 22, justifyContent: "center", width: 22 },
  benefitIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  benefitLabel: { color: tokens.color.textMuted, flexShrink: 1, fontSize: 14, lineHeight: 20 },
  benefitRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 46, paddingVertical: tokens.spacing.xs },
  benefitRowLast: { borderBottomWidth: 0 },
  benefitRows: { marginTop: -tokens.spacing.xs },
  benefitValue: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontWeight: tokens.weight.bold, lineHeight: 20, textAlign: "right" },
  copy: { flex: 1, gap: 4 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1 },
  planPriceChip: { alignItems: "center", borderRadius: tokens.radius.pill, justifyContent: "center", minHeight: 30, paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.xs },
  planPriceChipLabel: { color: tokens.color.surfaceApp, fontSize: 16, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.semibold },
  productName: { color: tokens.color.textMain, fontSize: 26, fontWeight: tokens.weight.extraBold },
  productTitleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  purchaseButton: { alignItems: "center", borderRadius: tokens.radius.lg, flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "center", marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 48, overflow: "hidden", paddingHorizontal: tokens.spacing.lg },
  purchaseButtonDisabled: { opacity: 0.45 },
  purchaseButtonLabel: { color: tokens.color.surfaceApp, fontSize: tokens.type.body, fontWeight: tokens.weight.extraBold },
  purchaseButtonPressed: { opacity: 0.72, transform: [{ translateY: 1 }] },
});
