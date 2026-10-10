import { HeartPulse, LockKeyhole, type LucideIcon } from "lucide-react-native";
import type { ReactNode } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { InlineNotice } from "@/components/ui";
import { tokens } from "@/design/tokens";

function ResponsibleUsePanel({ body, children, icon: Icon, title }: { body: string; children?: ReactNode; icon: LucideIcon; title: string }) {
  return (
    <View style={styles.panel}>
      <View style={styles.panelHeading}>
        <View style={styles.panelIcon}><Icon color={tokens.color.textMain} size={20} /></View>
        <Text style={styles.panelTitle}>{title}</Text>
      </View>
      <Text style={[styles.panelBody, children ? styles.panelBodyWithActions : undefined]}>{body}</Text>
      {children}
    </View>
  );
}

export function ResponsibleUseContent({ policyActions }: { policyActions?: ReactNode }) {
  return (
    <>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>Uso responsable</Text>
        <View style={styles.headerIcon}><LockKeyhole color={tokens.color.textMain} size={27} /></View>
        <Text style={styles.title}>Información importante antes de continuar</Text>
        <Text style={styles.description}>Revisa qué hace My Scoope, qué no hace y qué decisiones quedan bajo tu responsabilidad.</Text>
      </View>
      <View style={styles.panelStack}>
        <ResponsibleUsePanel
          body="No diagnostica, trata ni reemplaza atención profesional. Si tienes una condición médica, consulta a un profesional."
          icon={HeartPulse}
          title="No es atención médica"
        />
        <ResponsibleUsePanel
          body="Tú decides qué datos compartes y puedes eliminar tu cuenta. Las etiquetas se procesan temporalmente y no guardamos la foto salvo que actives “Guardar copia procesada”."
          icon={LockKeyhole}
          title="Privacidad y control"
        >
          {policyActions}
        </ResponsibleUsePanel>
      </View>
      <InlineNotice>Al continuar confirmas que comprendes estos límites. Podrás consultar las políticas completas cuando quieras.</InlineNotice>
    </>
  );
}

export function ResponsibleUseActionButton({ disabled = false, label = "Entiendo y quiero continuar", loading = false, onPress }: { disabled?: boolean; label?: string; loading?: boolean; onPress(): void }) {
  return (
    <Pressable accessibilityLabel={label} accessibilityRole="button" accessibilityState={{ busy: loading, disabled: disabled || loading }} disabled={disabled || loading} onPress={onPress} style={[styles.actionButton, (disabled || loading) && styles.actionDisabled]}>
      <Svg aria-hidden pointerEvents="none" style={StyleSheet.absoluteFill}>
        <Defs>
          <LinearGradient id="responsible-use-action" x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Rect fill="url(#responsible-use-action)" height="100%" width="100%" />
      </Svg>
      {loading ? <ActivityIndicator color={tokens.color.surfaceApp} /> : <Text style={styles.actionLabel}>{label}</Text>}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  header: { alignItems: "center", gap: tokens.spacing.sm },
  eyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.2, textTransform: "uppercase" },
  headerIcon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, height: 54, justifyContent: "center", marginTop: tokens.spacing.sm, width: 54 },
  title: { color: tokens.color.textMain, fontSize: 28, fontWeight: tokens.weight.extraBold, letterSpacing: -0.8, lineHeight: 32, marginTop: tokens.spacing.lg, textAlign: "center" },
  description: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23, textAlign: "center" },
  panelStack: { gap: tokens.spacing.sm },
  panel: { backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.lg, gap: tokens.spacing.md, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.card.outerPadding },
  panelHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  panelIcon: { alignItems: "center", backgroundColor: tokens.color.surfaceElevated, borderRadius: tokens.radius.md, height: 36, justifyContent: "center", width: 36 },
  panelTitle: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  panelBody: { color: tokens.color.textMuted, fontSize: 12, lineHeight: 17 },
  panelBodyWithActions: { marginBottom: tokens.spacing.sm },
  actionButton: { alignItems: "center", borderRadius: tokens.radius.lg, justifyContent: "center", minHeight: 48, overflow: "hidden", paddingHorizontal: tokens.spacing.lg },
  actionDisabled: { opacity: 0.55 },
  actionLabel: { color: tokens.color.surfaceApp, fontSize: tokens.type.body, fontWeight: tokens.weight.extraBold },
});
