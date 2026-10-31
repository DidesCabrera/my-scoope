import { MoreHorizontal, type LucideIcon } from "lucide-react-native";
import type { ReactNode } from "react";
import { useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import { EntityCardAction } from "@/components/ui";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
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
          <MoreHorizontal color={tokens.color.textMuted} size={17} />
        </EntityCardAction>
      )}
      <ActionSheetModal onRequestClose={close} visible={visible}>
          <SafeAreaView edges={["left", "right"]} style={styles.sheetSafeArea}>
            <ActionSheetHeader icon={MoreHorizontal} onClose={close} title={selected?.confirmation?.title ?? title} />

            <ScrollView
              contentContainerStyle={styles.sheetContent}
              keyboardShouldPersistTaps="handled"
              nestedScrollEnabled
              showsVerticalScrollIndicator={false}
              style={styles.sheetScroll}>
              {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}

              {!selected ? <ActionSheetActions>{actions.map((action) => {
                return (
                  <ActionSheetAction
                    destructive={action.destructive}
                    disabled={submitting}
                    icon={action.icon}
                    key={action.key}
                    label={action.label}
                    loading={submitting}
                    onPress={() => select(action)}
                  />
                );
              })}</ActionSheetActions> : (
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
            </ScrollView>
          </SafeAreaView>
      </ActionSheetModal>
    </>
  );
}

const styles = StyleSheet.create({
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  sheetScroll: { flexGrow: 0, flexShrink: 1 },
  sheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  confirmation: { gap: tokens.spacing.md },
  confirmationText: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  pressed: { opacity: 0.65 },
});
