import { StyleSheet, Text, View } from "react-native";

import { Button } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

export function CalendarPlanRemovalConfirmation({ busy = false, onCancel, onConfirm }: {
  busy?: boolean;
  onCancel(): void;
  onConfirm(): void;
}) {
  return <View style={styles.confirmation}>
    <Text style={styles.confirmationText}>La minuta dejará de estar asignada a esta fecha. La minuta de tu biblioteca y el historial permanecerán guardados. No se puede quitar si ya registraste cumplimiento.</Text>
    <Button label="Eliminar del calendario" loading={busy} onPress={onConfirm} style={styles.removeButton} variant="danger" />
    <Button disabled={busy} label="Cancelar" onPress={onCancel} variant="secondary" />
  </View>;
}

const styles = StyleSheet.create({
  confirmation: { gap: tokens.spacing.md },
  confirmationText: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23, marginBottom: 18 },
  removeButton: { backgroundColor: `${tokens.color.danger}1A` },
});
