import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import { Button, Card, InlineNotice, SectionTitle, textStyles } from "./primitives";

export function EmptyState({
  title,
  message,
  actionLabel,
  onAction,
}: {
  title: string;
  message: string;
  actionLabel?: string;
  onAction?(): void;
}) {
  return (
    <Card muted>
      <SectionTitle title={title} />
      <Text style={textStyles.muted}>{message}</Text>
      {actionLabel && onAction ? <Button label={actionLabel} onPress={onAction} variant="secondary" /> : null}
    </Card>
  );
}

export function RecoverableErrorState({ message, onRetry }: { message: string; onRetry(): void }) {
  return (
    <View style={styles.stateGroup}>
      <InlineNotice tone="error">{message}</InlineNotice>
      <Button label="Volver a intentar" onPress={onRetry} variant="secondary" />
    </View>
  );
}

export function ConfirmationState({
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  danger = false,
  busy = false,
}: {
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm(): void;
  onCancel(): void;
  danger?: boolean;
  busy?: boolean;
}) {
  const accent = danger ? tokens.color.danger : tokens.color.warning;
  return (
    <Card accent={accent} style={[styles.confirmationCard, { backgroundColor: `${accent}1A`, borderColor: `${accent}80`, borderTopColor: `${accent}80` }]}>
      <SectionTitle title={title} />
      <Text style={textStyles.muted}>{message}</Text>
      <View style={styles.actions}>
        <Pressable accessibilityRole="button" accessibilityState={{ disabled: busy }} disabled={busy} onPress={onCancel} style={[styles.actionChip, { borderColor: accent }, busy && styles.actionDisabled]}>
          <Text style={[styles.actionChipText, { color: accent }]}>Cancelar</Text>
        </Pressable>
        <Pressable accessibilityRole="button" accessibilityState={{ busy, disabled: busy }} disabled={busy} onPress={onConfirm} style={[styles.actionChip, styles.confirmChip, danger && { backgroundColor: accent }, busy && styles.actionDisabled]}>
          {busy ? <ActivityIndicator color={danger ? tokens.color.textMain : tokens.color.surfaceApp} /> : null}
          <Text style={[styles.confirmChipText, danger && styles.dangerConfirmText]}>{confirmLabel}</Text>
        </Pressable>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  actionChip: { alignItems: "center", borderRadius: tokens.radius.pill, borderWidth: 1, flex: 1, justifyContent: "center", minHeight: 44, paddingHorizontal: 12, paddingVertical: 8 },
  actionChipText: { fontSize: 16, fontWeight: "700", textAlign: "center" },
  actionDisabled: { opacity: 0.55 },
  actions: { flexDirection: "row", gap: tokens.spacing.sm },
  confirmationCard: { borderTopWidth: 1 },
  confirmChip: { backgroundColor: tokens.color.textMain, borderColor: "transparent" },
  confirmChipText: { color: tokens.color.surfaceApp, fontSize: 16, fontWeight: "700", textAlign: "center" },
  dangerConfirmText: { color: tokens.color.surfaceApp },
  stateGroup: { gap: tokens.spacing.md },
});

