import { BookPlus, Clock3, Copy, Info, MoreHorizontal, Pencil, Scale, Send, Trash2 } from "lucide-react-native";
import type { ReactNode } from "react";
import { useState } from "react";
import {
  Alert,
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
  ShareResource,
} from "@/api/types";
import { Button, Field, InlineNotice } from "@/components/ui/primitives";
import { EntityCardAction } from "@/components/ui";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { MealTimeForm } from "@/components/calendarization/calendarized-entity-actions";
import { tokens } from "@/design/tokens";
import { openNativeShare } from "@/sharing/native-share";

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

type LibraryActionsProps = {
  apiRequest: ApiRequest;
  entitySlug: "foods" | "meals" | "daily-plans" | "programs";
  item: Pick<LibraryItem, "actions" | "entity" | "id" | "name">;
  initialAction?: "change-time";
  mealTimeInMenu?: boolean;
  onCompleted(result: LibraryActionResult): void;
  onCompare?: () => void;
  onEdit?: () => void;
  onOpenInformation?: () => void;
  onRemove?: () => Promise<void>;
  onSaveToLibrary?: () => Promise<void>;
  onVisibleChange?: (visible: boolean) => void;
  renderTrigger?: (open: () => void) => ReactNode;
  visible?: boolean;
  mealTimeChange?: {
    initialTime?: string | null;
    onSubmit(hour: string): Promise<void>;
  };
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

export function LibraryActions({ apiRequest, entitySlug, initialAction, item, mealTimeChange, mealTimeInMenu = true, onCompleted, onCompare, onEdit, onOpenInformation, onRemove, onSaveToLibrary, onVisibleChange, renderTrigger, visible: controlledVisible }: LibraryActionsProps) {
  const actions = item.actions ?? [];
  const [internalVisible, setInternalVisible] = useState(false);
  const [selected, setSelected] = useState<LibraryAction | { destructive: false; key: "change-time"; label: string } | { destructive: true; key: "remove"; label: string } | null>(
    initialAction === "change-time" ? { destructive: false, key: "change-time", label: "Cambiar hora" } : null,
  );
  const [name, setName] = useState(item.name);
  const [submitting, setSubmitting] = useState(false);
  const [dismissShareImmediately, setDismissShareImmediately] = useState(false);
  const [shareResource, setShareResource] = useState<ShareResource | null>(null);
  const [error, setError] = useState<string | null>(null);
  const visible = controlledVisible ?? internalVisible;
  const setVisible = (nextVisible: boolean) => {
    if (controlledVisible === undefined) setInternalVisible(nextVisible);
    onVisibleChange?.(nextVisible);
  };

  if (!actions.length && !mealTimeChange && !onCompare && !onEdit && !onOpenInformation && !onRemove && !onSaveToLibrary) return null;

  const close = () => {
    if (submitting) return;
    setVisible(false);
    setSelected(null);
    setError(null);
  };

  const open = () => {
    setName(item.name);
    setDismissShareImmediately(false);
    setShareResource(null);
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

  const prepareShare = async () => {
    if (shareResource) return shareResource;
    const resource = await apiRequest<ShareResource>(`/api/v1/shares/${entitySlug}/${item.id}`, {
      body: JSON.stringify({ claim_policy: "multiple" }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
    setShareResource(resource);
    return resource;
  };

  const shareItem = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const resource = await prepareShare();
      setDismissShareImmediately(true);
      setVisible(false);
      setSelected(null);
      await new Promise<void>((resolve) => {
        requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
      });
      await openNativeShare(resource);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setDismissShareImmediately(false);
      setSubmitting(false);
    }
  };

  const selectAction = (action: LibraryAction) => {
    setError(null);
    if (action.key === "share") {
      void shareItem();
      return;
    }
    setSelected(action);
  };

  const removeItem = async () => {
    if (!onRemove) return;
    setSubmitting(true);
    setError(null);
    try {
      await onRemove();
      setVisible(false);
      setSelected(null);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  };

  const saveToLibrary = async () => {
    if (!onSaveToLibrary) return;
    setSubmitting(true);
    setError(null);
    try {
      await onSaveToLibrary();
      setVisible(false);
      setSelected(null);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  };

  const actionTitle = selected?.key === "delete"
    ? `¿Eliminar ${entityLabels[item.entity]}?`
    : selected?.key === "remove"
      ? "¿Quitar comida?"
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
      <ActionSheetModal dismissImmediately={dismissShareImmediately} onRequestClose={close} visible={visible}>
          <SafeAreaView edges={["left", "right"]} style={styles.sheetSafeArea}>
            <View style={styles.sheet}>
              <ActionSheetHeader entity={item.entity} onClose={close} title={actionTitle ?? item.name} />

              {!selected ? (
                <View style={styles.sheetContent}>
                  {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
                  <ActionSheetActions>
                {onOpenInformation ? (
                  <ActionSheetAction
                    icon={Info}
                    label="Ver información del elemento"
                    onPress={() => {
                      setVisible(false);
                      onOpenInformation();
                    }}
                  />
                ) : null}

                {onCompare ? (
                  <ActionSheetAction
                    icon={Scale}
                    label="Comparar"
                    onPress={() => {
                      setVisible(false);
                      onCompare();
                    }}
                  />
                ) : null}

                {onEdit ? (
                  <ActionSheetAction
                    icon={Pencil}
                    label="Editar"
                    onPress={() => {
                      setVisible(false);
                      onEdit();
                    }}
                  />
                ) : null}

                {onSaveToLibrary ? (
                  <ActionSheetAction
                    disabled={submitting}
                    icon={BookPlus}
                    label="Guardar en mi biblioteca"
                    onPress={() => void saveToLibrary()}
                  />
                ) : null}

                {actions.map((action) => {
                  const Icon = actionIcons[action.key];
                  return (
                    <ActionSheetAction
                      destructive={action.destructive}
                      disabled={submitting}
                      icon={Icon}
                      key={action.key}
                      label={action.label}
                      onPress={() => selectAction(action)}
                    />
                  );
                })}

                {mealTimeChange && mealTimeInMenu ? (
                  <ActionSheetAction
                    icon={Clock3}
                    label="Cambiar hora"
                    onPress={() => setSelected({ destructive: false, key: "change-time", label: "Cambiar hora" })}
                  />
                ) : null}

                {onRemove ? (
                  <ActionSheetAction
                    destructive
                    disabled={submitting}
                    icon={Trash2}
                    label="Quitar comida"
                    onPress={() => setSelected({ destructive: true, key: "remove", label: "Quitar comida" })}
                  />
                ) : null}
                  </ActionSheetActions>
                </View>
              ) : (
                <ScrollView automaticallyAdjustKeyboardInsets contentContainerStyle={styles.sheetContent} keyboardShouldPersistTaps="handled" nestedScrollEnabled showsVerticalScrollIndicator={false} style={styles.sheetScroll}>
                {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}

                {selected?.key === "change-time" && mealTimeChange ? (
                  <MealTimeForm initialTime={mealTimeChange.initialTime} onCancel={initialAction ? close : () => setSelected(null)} onSaved={close} onSubmit={mealTimeChange.onSubmit} />
                ) : null}

                {selected?.key === "rename" ? (
                  <View style={styles.form}>
                    <Field autoCapitalize="sentences" label="Nombre" onChangeText={setName} value={name} />
                    <Button disabled={!name.trim()} label="Guardar nombre" loading={submitting} onPress={() => void execute({ action: "rename", name })} />
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

                {selected?.key === "remove" ? (
                  <View style={styles.confirmation}>
                    <Text style={styles.confirmationText}>Se quitará esta comida del plan diario.</Text>
                    <Button label="Quitar comida" loading={submitting} onPress={() => void removeItem()} variant="danger" />
                    <Button label="Cancelar" onPress={() => setSelected(null)} variant="secondary" />
                  </View>
                ) : null}

                </ScrollView>
              )}
            </View>
          </SafeAreaView>
      </ActionSheetModal>
    </>
  );
}

const styles = StyleSheet.create({
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  sheet: { backgroundColor: tokens.color.surfaceCard },
  sheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  sheetScroll: { flexGrow: 0, flexShrink: 1 },
  form: { gap: tokens.spacing.md },
  confirmation: { gap: tokens.spacing.md },
  confirmationText: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
});
