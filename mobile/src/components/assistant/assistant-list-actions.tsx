import { Check, CircleCheck, Clock3, List, Plus, Sparkles, X, XCircle } from "lucide-react-native";
import type { LucideIcon } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";
import type { AssistantSection } from "./assistant-section-tabs";

export type ProposalFilter = "all" | "pending_review" | "approved" | "applied" | "rejected";

const proposalFilters: { icon: LucideIcon; label: string; value: ProposalFilter }[] = [
  { icon: List, label: "Ver todas", value: "all" },
  { icon: Clock3, label: "Ver pendientes", value: "pending_review" },
  { icon: CircleCheck, label: "Ver aprobadas", value: "approved" },
  { icon: Check, label: "Ver aplicadas", value: "applied" },
  { icon: XCircle, label: "Ver rechazadas", value: "rejected" },
];

type Props = {
  activeSection: AssistantSection;
  onClose(): void;
  onNewChat?(): void;
  onProposalFilterChange?(filter: ProposalFilter): void;
  proposalFilter?: ProposalFilter;
  visible: boolean;
};

export function AssistantListActions({ activeSection, onClose, onNewChat, onProposalFilterChange, proposalFilter = "all", visible }: Props) {
  const chooseFilter = (filter: ProposalFilter) => {
    onClose();
    onProposalFilterChange?.(filter);
  };
  const startChat = () => {
    onClose();
    onNewChat?.();
  };
  return (
    <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <View style={styles.header}>
          <View><Text style={styles.eyebrow}>ACCIONES</Text><Text style={styles.title}>{activeSection === "chats" ? "Chats" : "Propuestas"}</Text></View>
          <Pressable accessibilityLabel="Cerrar" accessibilityRole="button" onPress={onClose} style={({ pressed }) => [styles.close, pressed && styles.pressed]}><X color={tokens.color.textMain} size={22} /></Pressable>
        </View>
        <View style={styles.content}>
          {activeSection === "chats" ? (
            <ActionRow icon={Plus} label="Nuevo chat" onPress={startChat} />
          ) : proposalFilters.map((filter) => (
            <ActionRow icon={filter.icon} key={filter.value} label={filter.label} onPress={() => chooseFilter(filter.value)} selected={filter.value === proposalFilter} />
          ))}
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

function ActionRow({ icon: Icon, label, onPress, selected = false }: { icon: LucideIcon; label: string; onPress(): void; selected?: boolean }) {
  return (
    <Pressable accessibilityRole="button" accessibilityState={{ selected }} onPress={onPress} style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
      <View style={styles.icon}><Icon color={tokens.color.textMain} size={20} /></View>
      <Text style={styles.label}>{label}</Text>
      {selected ? <Sparkles color={tokens.color.textMain} size={18} /> : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  close: { alignItems: "center", height: 42, justifyContent: "center", width: 42 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.extraBold, letterSpacing: 1.1 },
  header: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  icon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 },
  label: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  pressed: { opacity: 0.65 },
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58 },
  safeArea: { backgroundColor: tokens.color.surfaceCard },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.extraBold, marginTop: 3 },
});
