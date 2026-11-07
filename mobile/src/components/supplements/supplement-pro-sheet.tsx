import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, Card } from "@/components/ui";
import { tokens } from "@/design/tokens";

export function SupplementProSheet({ onClose, visible }: { onClose(): void; visible: boolean }) {
  const router = useRouter();
  return <ActionSheetModal onRequestClose={onClose} visible={visible}>
    <View style={styles.content}>
      <Card accent={tokens.color.dailyPlan}>
        <Text style={styles.title}>Suplementos es una capacidad Pro</Text>
        <Text style={styles.body}>Con Pro puedes guardar tus suplementos, planificar ingestas y registrar su cumplimiento. Tus datos guardados se conservan si cambias de plan.</Text>
        <Button label="Ver Suscripciones y Bolsas" onPress={() => { onClose(); router.push("/subscription"); }} variant="gradient" />
        <Button label="Cerrar" onPress={onClose} variant="secondary" />
      </Card>
    </View>
  </ActionSheetModal>;
}

const styles = StyleSheet.create({
  body: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 22, marginBottom: tokens.spacing.md },
  content: { paddingHorizontal: tokens.spacing.screen, paddingBottom: tokens.spacing.md },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.extraBold, marginBottom: tokens.spacing.sm },
});
