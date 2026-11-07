import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import * as Crypto from "expo-crypto";
import { Pill, PillBottle, Trash2 } from "lucide-react-native";
import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, StyleSheet, View } from "react-native";
import { NestableScrollContainer } from "react-native-draggable-flatlist";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { EntitlementsData, Supplement, SupplementIntake } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedEntityActions } from "@/components/calendarization/calendarized-entity-actions";
import { EntityCompletionToggleCard } from "@/components/calendarization/meal-adherence-check-in";
import { EntityDetailPage, EntityDetailSection } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { SupplementIntakeItemsTable, type SupplementIntakeTableItem } from "@/components/supplements/supplement-intake-items-table";
import { consumeSupplementIntakeSelection } from "@/components/supplements/supplement-intake-selection-handoff";
import { SupplementProSheet } from "@/components/supplements/supplement-pro-sheet";
import { Button, HeaderMetadataChip, InlineNotice, LoadingState, NativeDateTimeField, SupplementCard } from "@/components/ui";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";
import { internalHref } from "@/navigation/internal-href";

type Picked = { supplement_id: number | null; item_id?: number; name?: string; quantity: string; unit: string };
type IntakePage = { items: SupplementIntake[] };
const units = ["capsule", "tablet", "softgel", "gummy", "sachet", "scoop", "drop", "ml", "g", "mg", "mcg", "iu", "tsp"] as const;

function pickedSignature(rows: Picked[]) {
  return JSON.stringify(rows.map(({ item_id, supplement_id, quantity, unit }) => ({ item_id, supplement_id, quantity, unit })));
}

export default function SupplementIntakeDetailScreen() {
  const { calendarizedDayId, id, intakeId, pinned, returnTo, selectedSupplementId, selectedSupplementNonce } = useLocalSearchParams<{ calendarizedDayId?: string; id: string; intakeId: string; pinned?: string; returnTo?: string; selectedSupplementId?: string; selectedSupplementNonce?: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const creating = intakeId === "new";
  const [pro, setPro] = useState(false);
  const [availableFeature, setAvailableFeature] = useState(false);
  const [upsell, setUpsell] = useState(false);
  const [available, setAvailable] = useState<Supplement[]>([]);
  const [selected, setSelected] = useState<Picked[]>([]);
  const [persistedSelected, setPersistedSelected] = useState<Picked[]>([]);
  const [hour, setHour] = useState("");
  const [label, setLabel] = useState("Nueva ingesta");
  const [actionSheet, setActionSheet] = useState<"change-time" | "menu" | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completionError, setCompletionError] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const [savingCompletion, setSavingCompletion] = useState(false);
  const initializedIntake = useRef(false);
  const handledSelection = useRef<string | null>(null);
  const failedAutoSave = useRef<string | null>(null);
  const selectedRef = useRef(selected);
  const selectorSession = useRef(0);
  const endpoint = `/api/v1/library/daily-plans/${id}/supplement-intakes`;
  const parsedCalendarizedDayId = Number(calendarizedDayId);
  const isCalendarizedContext = Number.isInteger(parsedCalendarizedDayId) && parsedCalendarizedDayId > 0;
  const isPinnedContext = pinned === "1";
  const liveEndpoint = isCalendarizedContext
    ? `/api/v1/days/${parsedCalendarizedDayId}/supplement-intakes`
    : isPinnedContext
      ? "/api/v1/today/pinned-plan/supplement-intakes"
      : null;
  const readEndpoint = liveEndpoint ?? endpoint;
  const fallbackHref = internalHref(returnTo) ?? `/libraries/daily-plans/${id}` as Href;
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: !creating && pro ? { icon: "more", label: `Más acciones para ${label}`, onPress: () => setActionSheet("menu") } : undefined,
      fallback: fallbackHref,
      forceFallback: true,
      mode: "back",
      secondaryAction: !creating && pro ? { icon: "clock", label: "Cambiar hora", onPress: () => setActionSheet("change-time") } : undefined,
      title: creating ? "Nueva ingesta" : label,
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [creating, fallbackHref, label, pro, setHeaderPresentation]));
  useFocusEffect(useCallback(() => {
    let active = true;
    void (async () => {
      try {
        const entitlements = await apiRequest<EntitlementsData>("/api/v1/entitlements", { cache: "no-store" });
        if (!active) return;
        const allowed = Boolean(entitlements.workspace_features?.can_use_supplements);
        setAvailableFeature(Boolean(entitlements.workspace_features?.supplements_available));
        setPro(allowed);
        if (!allowed) return;
        const products = (await apiRequest<{ items: Supplement[] }>("/api/v1/library/supplements")).items;
        if (!active) return;
        setAvailable(products);
        if (!creating && !initializedIntake.current) {
          const intake = (await apiRequest<{ items: SupplementIntake[] }>(readEndpoint)).items.find((row) => row.id === Number(intakeId));
          if (!intake) throw new Error("No encontramos esta ingesta.");
          if (active) {
            const picked = intake.items.map((item) => ({ item_id: item.id, supplement_id: item.supplement_id, name: String(item.supplement.name ?? "Suplemento guardado"), quantity: item.quantity, unit: item.unit }));
            setLabel(intake.label);
            setHour(intake.hour ?? "");
            setCompleted(intake.status === "completed");
            setSelected(picked);
            setPersistedSelected(picked);
            initializedIntake.current = true;
          }
        }
        const stagedSelection = consumeSupplementIntakeSelection(id, intakeId);
        const supplementId = stagedSelection?.supplementId ?? Number(selectedSupplementId);
        const selectionKey = stagedSelection
          ? `${supplementId}:${stagedSelection.selectionSession}`
          : `${supplementId}:${selectedSupplementNonce ?? "selected"}`;
        const selectedProduct = products.find((item) => item.id === supplementId);
        if (selectedProduct && handledSelection.current !== selectionKey) {
          handledSelection.current = selectionKey;
          setSelected((rows) => rows.some((row) => row.supplement_id === selectedProduct.id) ? rows : [...rows, {
            supplement_id: selectedProduct.id,
            quantity: selectedProduct.default_quantity ?? "1",
            unit: selectedProduct.default_unit || (selectedProduct.form === "powder" ? "g" : selectedProduct.form === "liquid" ? "ml" : units.includes(selectedProduct.form as typeof units[number]) ? selectedProduct.form : "capsule"),
          }]);
        }
      } catch (nextError) { if (active) setError(userFacingError(nextError)); }
      finally { if (active) setLoading(false); }
    })();
    return () => { active = false; };
  }, [apiRequest, creating, id, intakeId, readEndpoint, selectedSupplementId, selectedSupplementNonce]));
  useEffect(() => { selectedRef.current = selected; }, [selected]);
  useEffect(() => {
    if (creating || isCalendarizedContext || loading || saving || !initializedIntake.current) return;
    const signature = pickedSignature(selected);
    if (signature === pickedSignature(persistedSelected) || signature === failedAutoSave.current) return;
    const submitted = selected;
    setSaving(true); setError(null);
    void apiRequest<IntakePage>(`${endpoint}/${intakeId}`, {
      body: JSON.stringify({
        hour: hour || null,
        items: submitted.map(({ item_id, supplement_id, quantity, unit }) => ({ item_id, supplement_id, quantity, unit })),
      }),
      method: "PUT",
    }).then((page) => {
      failedAutoSave.current = null;
      const updated = page.items.find((row) => row.id === Number(intakeId));
      const savedRows = updated?.items.map((item) => ({ item_id: item.id, supplement_id: item.supplement_id, name: String(item.supplement.name ?? "Suplemento guardado"), quantity: item.quantity, unit: item.unit })) ?? submitted;
      setPersistedSelected(savedRows);
      if (pickedSignature(selectedRef.current) === signature) setSelected(savedRows);
    }).catch((nextError) => {
      failedAutoSave.current = signature;
      setError(userFacingError(nextError));
    }).finally(() => setSaving(false));
  }, [apiRequest, creating, endpoint, hour, intakeId, isCalendarizedContext, loading, persistedSelected, saving, selected]);
  async function changeHour(nextHour: string) {
    const page = isCalendarizedContext
      ? await apiRequest<IntakePage>(`${readEndpoint}/${intakeId}/hour`, { body: JSON.stringify({ hour: nextHour }), method: "PATCH" })
      : await apiRequest<IntakePage>(`${endpoint}/${intakeId}`, {
        body: JSON.stringify({
          hour: nextHour,
          items: persistedSelected.map(({ item_id, supplement_id, quantity, unit }) => ({ item_id, supplement_id, quantity, unit })),
        }),
        method: "PUT",
      });
    const updated = page.items.find((row) => row.id === Number(intakeId));
    setHour(updated?.hour ?? nextHour);
  }
  async function toggleCompletion(nextCompleted: boolean) {
    if (!liveEndpoint || savingCompletion) return;
    const previous = completed;
    setCompleted(nextCompleted);
    setSavingCompletion(true);
    setCompletionError(null);
    try {
      const page = await apiRequest<IntakePage>(`${liveEndpoint}/${intakeId}/check-ins`, {
        body: JSON.stringify({ action: nextCompleted ? "completed" : "skipped", idempotency_key: Crypto.randomUUID() }),
        method: "POST",
      });
      const updated = page.items.find((row) => row.id === Number(intakeId));
      setCompleted(updated?.status === "completed");
    } catch (nextError) {
      setCompleted(previous);
      setCompletionError(userFacingError(nextError));
    } finally { setSavingCompletion(false); }
  }
  async function save() {
    if (!selected.length) { setError("Elige al menos un suplemento."); return; }
    if (hour && !/^([01]\d|2[0-3]):[0-5]\d$/.test(hour)) { setError("Usa el formato de hora HH:MM."); return; }
    if (selected.some((row) => !(Number(row.quantity) > 0))) { setError("Escribe una cantidad válida para cada suplemento."); return; }
    setSaving(true); setError(null);
    try {
      await apiRequest(endpoint, { method: "POST", body: JSON.stringify({ hour: hour || null, items: selected.map(({ item_id, supplement_id, quantity, unit }) => ({ item_id, supplement_id, quantity, unit })) }) });
      if (router.canGoBack()) router.back();
      else router.replace(fallbackHref);
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setSaving(false); }
  }
  function remove() {
    Alert.alert("Eliminar ingesta", "Se quitará esta ingesta de la minuta.", [
      { text: "Cancelar", style: "cancel" },
      { text: "Eliminar", style: "destructive", onPress: () => { void apiRequest(`${isCalendarizedContext ? readEndpoint : endpoint}/${intakeId}`, { method: "DELETE" }).then(() => router.replace(fallbackHref)).catch((nextError) => setError(userFacingError(nextError))); } },
    ]);
  }
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Cargando ingesta…" />;
  const tableItems: SupplementIntakeTableItem[] = selected.map((row, index) => {
    const product = available.find((item) => item.id === row.supplement_id);
    return {
      brand: product?.brand,
      id: row.item_id != null ? `item:${row.item_id}` : row.supplement_id != null ? `supplement:${row.supplement_id}` : `draft:${index}`,
      name: product?.name ?? row.name ?? "Suplemento guardado",
      quantity: row.quantity,
      unit: row.unit,
    };
  });
  const selectedIndex = (item: SupplementIntakeTableItem) => tableItems.findIndex((row) => row.id === item.id);
  return <><NestableScrollContainer contentContainerStyle={styles.content} showsVerticalScrollIndicator={false} style={styles.screen}>
    <EntityDetailPage
      entity="supplement"
      eyebrow="Ingesta de suplementos"
      eyebrowAccessory={hour ? <HeaderMetadataChip kind="time" value={hour} /> : undefined}
      indicators={selected.length ? [{ icon: "supplement", label: "sups", value: selected.length }] : undefined}
      identityIcon={PillBottle}
      showNutrition={false}
      title={label}>
    {!availableFeature ? <InlineNotice tone="info">Las ingestas de suplementos aún no están disponibles.</InlineNotice> : !pro ? <Button label="Abrir Suplementos Pro" onPress={() => setUpsell(true)} variant="primary" /> : <>
      {!creating && liveEndpoint ? <EntityCompletionToggleCard completed={completed} entity="supplement" error={completionError} onToggle={(nextCompleted) => void toggleCompletion(nextCompleted)} saving={savingCompletion} /> : null}
      {creating ? <EntityDetailSection detail="Opcional" title="Horario de la ingesta">
        <NativeDateTimeField confirmationColor={tokens.color.supplement} iconColor={tokens.color.supplement} label="Hora de la ingesta" mode="time" onChange={setHour} value={hour} />
      </EntityDetailSection> : null}
      <EntityDetailSection detail={`${selected.length} ${selected.length === 1 ? "suplemento" : "suplementos"}`} title="Composición de la ingesta">
        <SupplementIntakeItemsTable
          editable={!isCalendarizedContext}
          items={tableItems}
          onOpen={(item) => {
            const index = selectedIndex(item);
            const supplementId = index >= 0 ? selected[index]?.supplement_id : null;
            if (supplementId) router.push(`/libraries/supplements/${supplementId}` as Href);
          }}
          onQuantityChange={isCalendarizedContext ? undefined : (item, quantity) => { const index = selectedIndex(item); if (index >= 0) setSelected((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, quantity } : row)); }}
          onRemove={isCalendarizedContext ? undefined : (item) => { const index = selectedIndex(item); if (index >= 0) setSelected((current) => current.filter((_, rowIndex) => rowIndex !== index)); }}
          onReorder={isCalendarizedContext ? undefined : (items) => setSelected((current) => items.flatMap((item) => { const index = tableItems.findIndex((row) => row.id === item.id); return index >= 0 && current[index] ? [current[index]] : []; }))}
        />
        {!isCalendarizedContext ? <View style={styles.addAction}><Button label="+ Agregar suplemento" onPress={() => {
          selectorSession.current += 1;
          const selectedIds = selected.flatMap((row) => row.supplement_id ? [row.supplement_id] : []).join(",");
          router.push(`/libraries/daily-plans/${id}/supplement-intakes/select?intakeId=${encodeURIComponent(intakeId)}&selectedIds=${encodeURIComponent(selectedIds)}&selectionSession=${selectorSession.current}${returnTo ? `&returnTo=${encodeURIComponent(returnTo)}` : ""}` as Href);
        }} variant="chipPrimary" /></View> : null}
      </EntityDetailSection>
      {selected.length ? <>
        <ProgramSectionHeader
          icon={Pill}
          subtitle="Revisa la información de cada suplemento incluido en esta ingesta."
          title="Detalle de cada suplemento"
        />
        <View style={styles.cardList}>
          {selected.map((row, index) => {
            const product = available.find((item) => item.id === row.supplement_id);
            const openDetail = row.supplement_id ? () => router.push(`/libraries/supplements/${row.supplement_id}` as Href) : undefined;
            return <SupplementCard
              brand={product?.brand}
              componentCount={product?.components.length ?? 0}
              key={row.item_id ?? `${row.supplement_id ?? "supplement"}-${index}`}
              name={product?.name ?? row.name ?? "Suplemento guardado"}
              onOpen={openDetail}
              quantity={row.quantity}
              unit={row.unit}
            />;
          })}
        </View>
      </> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {creating ? <Button label="Crear ingesta" loading={saving} onPress={() => void save()} variant="primary" /> : null}
    </>}
    {!pro && error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    </EntityDetailPage>
  </NestableScrollContainer>
  <SupplementProSheet onClose={() => setUpsell(false)} visible={upsell} />
  <ActionSheetModal onRequestClose={() => setActionSheet(null)} visible={actionSheet === "menu"}>
    <SafeAreaView edges={["left", "right"]} style={styles.sheetSafeArea}>
      <ActionSheetHeader icon={PillBottle} iconColor={tokens.color.supplement} onClose={() => setActionSheet(null)} title={label} />
      <View style={styles.sheetContent}>
        <ActionSheetActions>
          <ActionSheetAction destructive icon={Trash2} label="Eliminar ingesta" onPress={() => { setActionSheet(null); remove(); }} />
        </ActionSheetActions>
      </View>
    </SafeAreaView>
  </ActionSheetModal>
  <CalendarizedEntityActions
    entityName={label}
    initialAction="change-time"
    key={actionSheet === "change-time" ? `change-time-${hour}` : "closed-supplement-intake-time-change"}
    onVisibleChange={(visible) => { if (!visible) setActionSheet(null); }}
    timeChange={{ entity: "supplement", initialTime: hour, onSubmit: changeHour }}
    timeChangeInMenu={false}
    visible={actionSheet === "change-time"}
  />
  </>;
}

const styles = StyleSheet.create({
  addAction: { marginTop: tokens.spacing.md },
  cardList: { gap: tokens.spacing.lg, minWidth: 0 },
  content: { flexGrow: 1, paddingBottom: 60, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  sheetContent: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard },
});
