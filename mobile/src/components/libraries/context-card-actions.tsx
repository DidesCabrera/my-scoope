import { MoreHorizontal, X, type LucideIcon } from "lucide-react-native";
import type { ReactNode } from "react";
import { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import { EntityCardAction } from "@/components/ui";
import { ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, InlineNotice } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

export type ContextCardAction = {
  confirmation?: {
    confirmLabel?: string;
    message: string;
    title: string;
  };
  destructive?: boolean;
  icon: LucideIcon;
  key: string;
  label: string;
  onPress(): void | Promise<void>;
};

type ContextCardActionsProps = {
  actions: ContextCardAction[];
  label: string;
  renderTrigger?: (open: () => void) => ReactNode;
  title: string;
};

export function ContextCardActions({ actions, label, renderTrigger, title }: ContextCardActionsProps) {
  const [visible, setVisible] = useState(false);
  const [selected, setSelected] = useState<ContextCardAction | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!actions.length) return null;

  const close = () => {
    if (submitting) return;
    setVisible(false);
    setSelected(null);
    setError(null);
  };

  const open = () => {
    setSelected(null);
    setError(null);
    setVisible(true);
  };

  const execute = async (action: ContextCardAction) => {
    setSubmitting(true);
    setError(null);
    try {
      await action.onPress();
      setVisible(false);
      setSelected(null);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  };

  const select = (action: ContextCardAction) => {
    if (action.confirmation) {
      setSelected(action);
      return;
    }
    void execute(action);
  };

  return (
    <>
      {renderTrigger ? renderTrigger(open) : (
        <EntityCardAction label={label} onPress={open}>
          <MoreHorizontal color={tokens.color.textMuted} size={21} />
        </EntityCardAction>
      )}
      <ActionSheetModal onRequestClose={close} visible={visible}>
          <SafeAreaView edges={["left", "right"]} style={styles.sheetSafeArea}>
            <View style={styles.sheetHeader}>
              <View style={styles.headerCopy}>
                <Text style={styles.eyebrow}>ACCIONES</Text>
                <Text numberOfLines={2} style={styles.title}>{selected?.confirmation?.title ?? title}</Text>
              </View>
              <Pressable accessibilityLabel="Cerrar" accessibilityRole="button" onPress={close} style={({ pressed }) => [styles.closeButton, pressed && styles.pressed]}>
                <X color={tokens.color.textMain} size={22} />
              </Pressable>
            </View>

            <View style={styles.sheetContent}>
              {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}

              {!selected ? actions.map((action) => {
                const Icon = action.icon;
                return (
                  <Pressable
                    accessibilityRole="button"
                    disabled={submitting}
                    key={action.key}
                    onPress={() => select(action)}
                    style={({ pressed }) => [styles.actionRow, pressed && styles.pressed]}>
                    <View style={styles.actionIcon}>
                      <Icon color={action.destructive ? tokens.color.danger : tokens.color.textMain} size={20} />
                    </View>
                    <Text style={[styles.actionLabel, action.destructive && styles.actionLabelDanger]}>{action.label}</Text>
                    {submitting ? <ActivityIndicator color={tokens.color.interactivePrimary} size="small" /> : null}
                  </Pressable>
                );
              }) : (
                <View style={styles.confirmation}>
                  <Text style={styles.confirmationText}>{selected.confirmation?.message}</Text>
                  <Button
                    label={selected.confirmation?.confirmLabel ?? selected.label}
                    loading={submitting}
                    onPress={() => void execute(selected)}
                    variant={selected.destructive ? "danger" : "primary"}
                  />
                  <Button disabled={submitting} label="Cancelar" onPress={() => setSelected(null)} variant="secondary" />
                </View>
              )}
            </View>
          </SafeAreaView>
      </ActionSheetModal>
    </>
  );
}

const styles = StyleSheet.create({
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, borderTopLeftRadius: tokens.radius.card, borderTopRightRadius: tokens.radius.card, maxHeight: "88%", overflow: "hidden" },
  sheetHeader: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  headerCopy: { flex: 1, gap: 3, minWidth: 0 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "800", letterSpacing: 1.1 },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  closeButton: { alignItems: "center", height: 42, justifyContent: "center", width: 42 },
  sheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  actionRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58, paddingVertical: tokens.spacing.sm },
  actionIcon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 },
  actionLabel: { color: tokens.color.textMain, flex: 1, fontSize: 16, fontWeight: "700" },
  actionLabelDanger: { color: tokens.color.danger },
  confirmation: { gap: tokens.spacing.md },
  confirmationText: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  pressed: { opacity: 0.65 },
});
