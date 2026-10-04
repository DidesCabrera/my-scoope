import { ListRestart, Scale } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";
import type { EntityKind } from "@/components/ui";

export function LibraryListActions({ canCompare, entity, onClose, onCompare, onEdit, title, visible }: { canCompare: boolean; entity: EntityKind; onClose(): void; onCompare(): void; onEdit(): void; title: string; visible: boolean }) {
  const actions = [
    { icon: ListRestart, label: "Editar lista", onPress: onEdit },
    ...(canCompare ? [{ icon: Scale, label: "Comparar", onPress: onCompare }] : []),
  ];
  return <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <View style={styles.sheet}>
          <ActionSheetHeader entity={entity} onClose={onClose} title={`Administrar ${title.toLowerCase()}`} />
          <View style={styles.content}><ActionSheetActions>{actions.map(({ icon, label, onPress }) => <ActionSheetAction icon={icon} key={label} label={label} onPress={onPress} />)}</ActionSheetActions></View>
        </View>
      </SafeAreaView>
  </ActionSheetModal>;
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: tokens.color.surfaceCard }, sheet: { backgroundColor: tokens.color.surfaceCard }, content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
});
