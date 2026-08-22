import { Copy, MoreHorizontal, Pencil, Send, Trash2, X } from "lucide-react-native";
import type { ReactNode } from "react";
import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type {
  LibraryAction,
  LibraryActionInput,
  LibraryActionKey,
  LibraryActionResult,
  LibraryItem,
} from "@/api/types";
import { Button, Field, InlineNotice } from "@/components/ui/primitives";
import { EntityCardAction } from "@/components/ui";
import { tokens } from "@/design/tokens";

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

type LibraryActionsProps = {
  apiRequest: ApiRequest;
  entitySlug: "foods" | "meals" | "daily-plans" | "programs";
  item: LibraryItem;
  onCompleted(result: LibraryActionResult): void;
  onVisibleChange?: (visible: boolean) => void;
  renderTrigger?: (open: () => void) => ReactNode;
  visible?: boolean;
};

const actionIcons = {
  rename: Pencil,
  duplicate: Copy,
  share: Send,
  delete: Trash2,
} as const;

const entityLabels = {
  food: "este alimento",
  meal: "esta comida",
  dailyPlan: "este plan diario",
  program: "este programa",
} as const;

export function LibraryActions({ apiRequest, entitySlug, item, onCompleted, onVisibleChange, renderTrigger, visible: controlledVisible }: LibraryActionsProps) {
  const actions = item.actions ?? [];
  const [internalVisible, setInternalVisible] = useState(false);
  const [selected, setSelected] = useState<LibraryAction | null>(null);
  const [name, setName] = useState(item.name);
  const [recipientEmail, setRecipientEmail] = useState("");
  const [subject, setSubject] = useState(item.name);
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const visible = controlledVisible ?? internalVisible;
  const setVisible = (nextVisible: boolean) => {
    if (controlledVisible === undefined) setInternalVisible(nextVisible);
    onVisibleChange?.(nextVisible);
  };

  if (!actions.length) return null;

  const close = () => {
    if (submitting) return;
    setVisible(false);
    setSelected(null);
    setError(null);
  };

  const open = () => {
    setName(item.name);
    setSubject(item.name);
    setRecipientEmail("");
    setMessage("");
    setSelected(null);
    setError(null);
    setVisible(true);
  };

  const execute = async (payload: LibraryActionInput) => {
    setSubmitting(true);
    setError(null);
    try {
      const result = await apiRequest<LibraryActionResult>(`/api/v1/library/${entitySlug}/${item.id}/actions`, {
        body: JSON.stringify(payload),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      setVisible(false);
      setSelected(null);
      onCompleted(result);
      Alert.alert("Listo", result.message);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  };

  const selectAction = (action: LibraryAction) => {
    setError(null);
    setSelected(action);
  };

  const actionTitle = selected?.key === "delete"
    ? `¿Eliminar ${entityLabels[item.entity]}?`
    : selected?.key === "duplicate"
      ? `¿Duplicar ${entityLabels[item.entity]}?`
      : selected?.label;

  return (
    <>
      {renderTrigger ? renderTrigger(open) : (
        <EntityCardAction label={`Más acciones para ${item.name}`} onPress={open}>
          <MoreHorizontal color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
        </EntityCardAction>
      )}
      <Modal animationType="fade" onRequestClose={close} transparent visible={visible}>
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.modalRoot}>
          <Pressable accessibilityLabel="Cerrar acciones" onPress={close} style={styles.scrim} />
          <SafeAreaView edges={["bottom", "left", "right"]} style={styles.sheetSafeArea}>
            <View style={styles.sheet}>
              <View style={styles.sheetHeader}>
                <View style={styles.headerCopy}>
                  <Text style={styles.eyebrow}>ACCIONES</Text>
                  <Text numberOfLines={1} style={styles.title}>{actionTitle ?? item.name}</Text>
                </View>
                <Pressable accessibilityLabel="Cerrar" accessibilityRole="button" onPress={close} style={({ pressed }) => [styles.closeButton, pressed && styles.pressed]}>
                  <X color={tokens.color.textMain} size={22} />
                </Pressable>
              </View>

              <ScrollView contentContainerStyle={styles.sheetContent} keyboardShouldPersistTaps="handled">
                {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}

                {!selected ? actions.map((action) => {
                  const Icon = actionIcons[action.key];
                  return (
                    <Pressable
                      accessibilityRole="button"
                      key={action.key}
                      onPress={() => selectAction(action)}
                      style={({ pressed }) => [styles.actionRow, pressed && styles.pressed]}>
                      <View style={[styles.actionIcon, action.destructive && styles.actionIconDanger]}>
                        <Icon color={action.destructive ? tokens.color.danger : tokens.color.textMain} size={20} />
                      </View>
                      <Text style={[styles.actionLabel, action.destructive && styles.actionLabelDanger]}>{action.label}</Text>
                    </Pressable>
                  );
                }) : null}

                {selected?.key === "rename" ? (
                  <View style={styles.form}>
                    <Field autoCapitalize="sentences" label="Nombre" onChangeText={setName} value={name} />
                    <Button disabled={!name.trim()} label="Guardar nombre" loading={submitting} onPress={() => void execute({ action: "rename", name })} />
                    <Button label="Volver" onPress={() => setSelected(null)} variant="secondary" />
                  </View>
                ) : null}

                {selected?.key === "share" ? (
                  <View style={styles.form}>
                    <Field keyboardType="email-address" label="Correo del destinatario" onChangeText={setRecipientEmail} placeholder="persona@correo.com" value={recipientEmail} />
                    <Field autoCapitalize="sentences" label="Asunto" onChangeText={setSubject} value={subject} />
                    <Field autoCapitalize="sentences" label="Mensaje (opcional)" multiline onChangeText={setMessage} value={message} />
                    <Button disabled={!recipientEmail.trim()} label="Compartir" loading={submitting} onPress={() => void execute({ action: "share", message, recipient_email: recipientEmail, subject })} />
                    <Button label="Volver" onPress={() => setSelected(null)} variant="secondary" />
                  </View>
                ) : null}

                {selected?.key === "duplicate" || selected?.key === "delete" ? (
                  <View style={styles.confirmation}>
                    <Text style={styles.confirmationText}>
                      {selected.key === "delete"
                        ? "Esta acción no se puede deshacer."
                        : `Se creará una copia de “${item.name}” en tu librería.`}
                    </Text>
                    <Button
                      label={selected.label}
                      loading={submitting}
                      onPress={() => void execute({ action: selected.key as Extract<LibraryActionKey, "duplicate" | "delete"> })}
                      variant={selected.key === "delete" ? "danger" : "primary"}
                    />
                    <Button label="Cancelar" onPress={() => setSelected(null)} variant="secondary" />
                  </View>
                ) : null}

                {submitting && !selected ? <ActivityIndicator color={tokens.color.interactivePrimary} /> : null}
              </ScrollView>
            </View>
          </SafeAreaView>
        </KeyboardAvoidingView>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  modalRoot: { flex: 1, justifyContent: "flex-end" },
  scrim: { backgroundColor: "rgba(20, 24, 22, 0.42)", bottom: 0, left: 0, position: "absolute", right: 0, top: 0 },
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, borderTopLeftRadius: tokens.radius.card, borderTopRightRadius: tokens.radius.card, maxHeight: "88%", overflow: "hidden" },
  sheet: { backgroundColor: tokens.color.surfaceCard },
  sheetHeader: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  headerCopy: { flex: 1, gap: 3, minWidth: 0 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "800", letterSpacing: 1.1 },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  closeButton: { alignItems: "center", height: 42, justifyContent: "center", width: 42 },
  sheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  actionRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58, paddingVertical: tokens.spacing.sm },
  actionIcon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 },
  actionIconDanger: { backgroundColor: tokens.color.surfaceMuted },
  actionLabel: { color: tokens.color.textMain, flex: 1, fontSize: 16, fontWeight: "700" },
  actionLabelDanger: { color: tokens.color.danger },
  form: { gap: tokens.spacing.md },
  confirmation: { gap: tokens.spacing.md },
  confirmationText: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  pressed: { opacity: 0.65 },
});
