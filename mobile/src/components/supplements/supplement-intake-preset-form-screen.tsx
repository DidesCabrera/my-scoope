import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useRef, useState } from "react";
import { KeyboardAvoidingView, Platform, StyleSheet, Text, View } from "react-native";
import { NestableScrollContainer } from "react-native-draggable-flatlist";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { Supplement, SupplementIntakePreset } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { SupplementIntakeItemsTable, type SupplementIntakeTableItem } from "@/components/supplements/supplement-intake-items-table";
import { consumePresetSupplementSelection } from "@/components/supplements/supplement-intake-preset-selection-handoff";
import { Button, CollectionPageHeader, InlineNotice, LoadingState } from "@/components/ui";
import { Field } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";
import { internalHref } from "@/navigation/internal-href";

type Picked = { item_id?: number; name?: string; quantity: string; supplement_id: number | null; unit: string };
const units = ["capsule", "tablet", "softgel", "gummy", "sachet", "scoop", "drop", "ml", "g", "mg", "mcg", "iu", "tsp"] as const;

export function SupplementIntakePresetFormScreen({ presetId }: { presetId: string }) {
  const creating = presetId === "new";
  const { returnTo } = useLocalSearchParams<{ returnTo?: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [name, setName] = useState("");
  const [available, setAvailable] = useState<Supplement[]>([]);
  const [selected, setSelected] = useState<Picked[]>([]);
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(creating);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initialized = useRef(creating);
  const handledSelection = useRef<string | null>(null);
  const selectorSession = useRef(0);
  const requestedReturnHref = internalHref(returnTo);
  const fallbackHref = requestedReturnHref ?? (creating ? "/libraries/supplements?tab=intakes" as Href : `/libraries/supplements/intakes/${presetId}` as Href);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: fallbackHref, forceFallback: true, mode: "back", title: creating ? "Crear ingesta" : "Editar ingesta" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [creating, fallbackHref, setHeaderPresentation]));
  useFocusEffect(useCallback(() => {
    let active = true;
    setLoading(true); setError(null);
    void (async () => {
      try {
        const products = (await apiRequest<{ items: Supplement[] }>("/api/v1/library/supplements")).items;
        if (!active) return;
        setAvailable(products);
        if (!creating && !initialized.current) {
          const preset = await apiRequest<SupplementIntakePreset>(`/api/v1/library/supplement-intake-presets/${presetId}`);
          if (!active) return;
          setName(preset.name);
          setSelected(preset.items.map((item) => ({ item_id: item.id, supplement_id: item.supplement_id, name: String(item.supplement.name ?? "Suplemento guardado"), quantity: item.quantity, unit: item.unit })));
          initialized.current = true;
        }
        const staged = consumePresetSupplementSelection(presetId);
        const selectedProduct = staged ? products.find((item) => item.id === staged.supplementId) : undefined;
        const selectionKey = staged ? `${staged.supplementId}:${staged.selectionSession}` : null;
        if (selectedProduct && selectionKey && handledSelection.current !== selectionKey) {
          handledSelection.current = selectionKey;
          setSelected((rows) => rows.some((row) => row.supplement_id === selectedProduct.id) ? rows : [...rows, {
            supplement_id: selectedProduct.id,
            quantity: selectedProduct.default_quantity ?? "1",
            unit: selectedProduct.default_unit || (selectedProduct.form === "powder" ? "g" : selectedProduct.form === "liquid" ? "ml" : units.includes(selectedProduct.form as typeof units[number]) ? selectedProduct.form : "capsule"),
          }]);
        }
      } catch (nextError) { if (active) setError(userFacingError(nextError)); }
      finally { if (active) { setLoading(false); setReady(true); } }
    })();
    return () => { active = false; };
  }, [apiRequest, creating, presetId]));

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
  async function save() {
    if (!name.trim()) { setError("Escribe un nombre para la ingesta."); return; }
    if (!selected.length) { setError("Agrega al menos un suplemento."); return; }
    if (selected.some((row) => row.supplement_id == null || !(Number(row.quantity) > 0))) { setError("Revisa los suplementos y sus dosis."); return; }
    setSaving(true); setError(null);
    try {
      const saved = await apiRequest<SupplementIntakePreset>(creating ? "/api/v1/library/supplement-intake-presets" : `/api/v1/library/supplement-intake-presets/${presetId}`, {
        method: creating ? "POST" : "PUT",
        body: JSON.stringify({ name: name.trim(), items: selected.map(({ supplement_id, quantity, unit }) => ({ supplement_id, quantity, unit })) }),
      });
      if (creating && requestedReturnHref) router.replace(requestedReturnHref);
      else if (!creating && router.canGoBack()) router.back();
      else router.replace(`/libraries/supplements/intakes/${saved.id}` as Href);
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setSaving(false); }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !ready) return <LoadingState label="Cargando ingesta…" />;
  return <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.flex}>
      <NestableScrollContainer automaticallyAdjustKeyboardInsets contentContainerStyle={styles.content} keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        <CollectionPageHeader entity="supplement" title={creating ? "Crear nueva ingesta" : "Editar ingesta"} />
        <View style={styles.section}>
          <Field autoCapitalize="sentences" label="Nombre" onChangeText={setName} placeholder="Ej: Suplementos de la mañana" value={name} />
        </View>
        <View style={styles.section}>
          <View style={styles.sectionHeading}><Text style={styles.heading}>Composición de la ingesta</Text><Text style={styles.helper}>Esta combinación podrá agregarse a distintas minutas.</Text></View>
          {selected.length ? <SupplementIntakeItemsTable
            items={tableItems}
            onOpen={(item) => { const index = selectedIndex(item); const supplementId = index >= 0 ? selected[index]?.supplement_id : null; if (supplementId) router.push(`/libraries/supplements/${supplementId}` as Href); }}
            onQuantityChange={(item, quantity) => { const index = selectedIndex(item); if (index >= 0) setSelected((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, quantity } : row)); }}
            onRemove={(item) => { const index = selectedIndex(item); if (index >= 0) setSelected((rows) => rows.filter((_, rowIndex) => rowIndex !== index)); }}
            onReorder={(items) => setSelected((current) => items.flatMap((item) => { const index = tableItems.findIndex((row) => row.id === item.id); return index >= 0 && current[index] ? [current[index]] : []; }))}
          /> : null}
          <View style={styles.addAction}><Button label="+ Agregar suplemento" onPress={() => {
            selectorSession.current += 1;
            router.push(`/libraries/supplements/intakes/select?presetId=${encodeURIComponent(presetId)}&selectedIds=${encodeURIComponent(selected.flatMap((row) => row.supplement_id ? [row.supplement_id] : []).join(","))}&selectionSession=${selectorSession.current}${requestedReturnHref ? `&returnTo=${encodeURIComponent(String(requestedReturnHref))}` : ""}` as Href);
          }} variant="chipPrimary" /></View>
        </View>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <Button disabled={!name.trim() || !selected.length || saving} label={creating ? "Crear ingesta" : "Guardar cambios"} loading={saving} onPress={() => void save()} variant="primary" />
      </NestableScrollContainer>
    </KeyboardAvoidingView>
  </SafeAreaView>;
}

const styles = StyleSheet.create({
  addAction: { marginTop: tokens.spacing.sm },
  content: { flexGrow: 1, gap: tokens.spacing.xl, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  flex: { flex: 1 },
  heading: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.extraBold },
  helper: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 20 },
  safeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  section: { gap: tokens.spacing.lg },
  sectionHeading: { gap: tokens.spacing.xs },
});
