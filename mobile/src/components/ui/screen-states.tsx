import { StyleSheet, Text, View } from "react-native";

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
  return (
    <Card accent={danger ? tokens.color.danger : tokens.color.warning}>
      <SectionTitle title={title} />
      <Text style={textStyles.muted}>{message}</Text>
      <View style={styles.actions}>
        <View style={styles.action}><Button disabled={busy} label="Cancelar" onPress={onCancel} variant="secondary" /></View>
        <View style={styles.action}><Button label={confirmLabel} loading={busy} onPress={onConfirm} variant={danger ? "danger" : "primary"} /></View>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  action: { flex: 1 },
  actions: { flexDirection: "row", gap: tokens.spacing.sm },
  stateGroup: { gap: tokens.spacing.md },
});

