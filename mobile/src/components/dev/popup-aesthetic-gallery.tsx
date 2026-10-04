import { CheckCircle2, ListRestart, Scale, Share2, Trash2, TriangleAlert, X } from "lucide-react-native";
import type { LucideIcon } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import { EntityIcon } from "@/components/ui";

function PreviewLabel({ children }: { children: string }) {
  return <Text style={styles.previewLabel}>{children}</Text>;
}

function ActionRow({ danger = false, icon: Icon, label, last = false }: { danger?: boolean; icon: LucideIcon; label: string; last?: boolean }) {
  const color = danger ? tokens.color.danger : tokens.color.textMain;
  return <View style={[styles.actionRow, last && styles.lastActionRow]}><Icon color={color} size={18} strokeWidth={2} /><Text style={[styles.actionText, danger && styles.dangerText]}>{label}</Text></View>;
}

export function PopupAestheticGallery() {
  return (
    <View style={styles.gallery}>
      <PreviewLabel>Menú inferior</PreviewLabel>
      <View style={[styles.stage, styles.sheetStage]}>
        <View style={styles.scrim} />
        <View style={styles.sheet}>
          <View style={styles.handle} />
          <View style={styles.sheetHeader}>
            <View style={styles.sheetIdentity}>
              <EntityIcon entity="dailyPlan" size="header" />
              <Text style={styles.sheetTitle}>Administrar librería</Text>
            </View>
            <X color={tokens.color.textMain} size={23} strokeWidth={2.2} />
          </View>
          <View style={styles.sheetContent}>
            <Text style={styles.actionsEyebrow}>ACCIONES</Text>
            <View style={styles.actionTable}>
              <ActionRow icon={ListRestart} label="Editar lista" />
              <ActionRow icon={Scale} label="Comparar" />
              <ActionRow icon={Share2} label="Compartir" />
              <ActionRow danger icon={Trash2} label="Eliminar selección" last />
            </View>
          </View>
        </View>
      </View>

      <PreviewLabel>Confirmación</PreviewLabel>
      <View style={styles.stage}>
        <View style={styles.scrim} />
        <View style={styles.dialog}>
          <View style={styles.warningIcon}><TriangleAlert color={tokens.color.danger} size={22} strokeWidth={2.2} /></View>
          <Text style={styles.dialogTitle}>Eliminar elemento</Text>
          <Text style={styles.dialogBody}>Esta acción no se puede deshacer.</Text>
          <View style={styles.dialogActions}>
            <View style={styles.secondaryButton}><Text style={styles.secondaryButtonText}>Cancelar</Text></View>
            <View style={styles.dangerButton}><Text style={styles.primaryButtonText}>Eliminar</Text></View>
          </View>
        </View>
      </View>

      <PreviewLabel>Aviso informativo</PreviewLabel>
      <View style={styles.stage}>
        <View style={styles.scrim} />
        <View style={styles.dialog}>
          <Text style={styles.dialogTitle}>Cambio guardado</Text>
          <Text style={styles.dialogBody}>La actualización ya está disponible.</Text>
          <View style={styles.primaryButton}><Text style={styles.primaryButtonText}>Entendido</Text></View>
        </View>
      </View>

      <PreviewLabel>Operación completada</PreviewLabel>
      <View style={styles.stage}>
        <View style={styles.scrim} />
        <View style={styles.statusCard}>
          <CheckCircle2 color={tokens.color.success} size={36} strokeWidth={2.2} />
          <Text style={styles.statusText}>Cambios guardados</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  actionRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 54, paddingHorizontal: tokens.spacing.lg },
  actionTable: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, overflow: "hidden" },
  actionsEyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1, marginBottom: tokens.spacing.sm },
  actionText: { color: tokens.color.textMain, flex: 1, fontSize: 15, fontWeight: tokens.weight.medium },
  dangerButton: { alignItems: "center", backgroundColor: tokens.color.danger, borderRadius: tokens.radius.lg, flex: 1, paddingVertical: tokens.spacing.sm + 2 },
  dangerText: { color: tokens.color.danger },
  dialog: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, marginHorizontal: tokens.spacing.xl, padding: tokens.spacing.lg, width: "78%" },
  dialogActions: { flexDirection: "row", gap: tokens.spacing.sm, marginTop: tokens.spacing.lg, width: "100%" },
  dialogBody: { color: tokens.color.textMuted, fontSize: 14, lineHeight: 20, marginTop: tokens.spacing.xs, textAlign: "center" },
  dialogTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold, textAlign: "center" },
  gallery: { gap: tokens.spacing.sm },
  handle: { alignSelf: "center", backgroundColor: tokens.color.borderStrong, borderRadius: tokens.radius.pill, height: 4, marginBottom: tokens.spacing.md, width: 40 },
  lastActionRow: { borderBottomWidth: 0 },
  previewLabel: { color: tokens.color.textMuted, fontSize: 13, fontWeight: tokens.weight.semibold, marginTop: tokens.spacing.sm },
  primaryButton: { alignItems: "center", alignSelf: "stretch", backgroundColor: tokens.color.textMain, borderRadius: tokens.radius.lg, marginTop: tokens.spacing.lg, paddingVertical: tokens.spacing.sm + 2 },
  primaryButtonText: { color: tokens.color.surfaceApp, fontSize: 14, fontWeight: tokens.weight.semibold },
  scrim: { backgroundColor: "rgba(20, 24, 22, 0.42)", bottom: 0, left: 0, position: "absolute", right: 0, top: 0 },
  secondaryButton: { alignItems: "center", borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, flex: 1, paddingVertical: tokens.spacing.sm + 2 },
  secondaryButtonText: { color: tokens.color.textMain, fontSize: 14, fontWeight: tokens.weight.semibold },
  sheet: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderTopLeftRadius: tokens.radius.card, borderTopRightRadius: tokens.radius.card, borderWidth: 1, bottom: 0, left: 0, paddingTop: tokens.spacing.sm, position: "absolute", right: 0 },
  sheetContent: { paddingBottom: tokens.spacing.lg, paddingHorizontal: tokens.spacing.lg, paddingTop: tokens.spacing.md },
  sheetHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", paddingBottom: tokens.spacing.md, paddingHorizontal: tokens.spacing.lg },
  sheetIdentity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  sheetTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  stage: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, height: 230, justifyContent: "center", overflow: "hidden", position: "relative" },
  sheetStage: { height: 390, justifyContent: "flex-end" },
  statusCard: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.md, minWidth: 220, paddingHorizontal: tokens.spacing.xl, paddingVertical: tokens.spacing.xl },
  statusText: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  warningIcon: { alignItems: "center", backgroundColor: `${tokens.color.danger}14`, borderRadius: tokens.radius.pill, height: 42, justifyContent: "center", marginBottom: tokens.spacing.sm, width: 42 },
});
