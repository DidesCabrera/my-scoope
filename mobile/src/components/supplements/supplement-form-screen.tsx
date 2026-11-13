import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { KeyboardAvoidingView, type NativeScrollEvent, type NativeSyntheticEvent, Platform, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { EntitlementsData, Supplement } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { isHeaderIdentityVisible } from "@/components/navigation/header-scroll";
import { SupplementProSheet } from "@/components/supplements/supplement-pro-sheet";
import { SupplementChoiceGrid } from "@/components/supplements/supplement-choice-grid";
import { SupplementFormPicker } from "@/components/supplements/supplement-form-picker";
import { defaultUnitForSupplementForm, editableSupplementForm, supplementForms } from "@/components/supplements/supplement-form-units";
import { Button, CollectionPageHeader, InlineNotice, LoadingState } from "@/components/ui";
import { Field } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";
import { internalHref } from "@/navigation/internal-href";

const unitLabels: Record<string, string> = { capsule: "Cápsula", tablet: "Comprimido", softgel: "Cápsula blanda", gummy: "Gomita", sachet: "Sobre", powder: "Polvo", liquid: "Líquido", scoop: "Medida", drop: "Gota", ml: "ml", g: "g", mg: "mg", mcg: "mcg", iu: "UI", tsp: "Cucharadita" };
const componentUnits = ["g", "mg", "mcg", "ml", "iu"] as const;
type ComponentDraft = { name: string; quantity: string; unit: string };
type NutritionKey = keyof Supplement["nutrition"];
type NutritionDraft = Record<NutritionKey, string>;
type SupplementDraft = Omit<Supplement, "id" | "components" | "default_quantity" | "default_unit" | "nutrition"> & { components: ComponentDraft[]; default_quantity: string; nutrition: NutritionDraft };
const blankNutrition: NutritionDraft = { energy_kcal: "", protein_g: "", carbs_g: "", fat_g: "", saturated_fat_g: "", sugar_g: "", fiber_g: "", sodium_mg: "" };
const blank: SupplementDraft = { name: "", brand: "", form: "", description: "", user_information: "", components: [], default_quantity: "", nutrition: blankNutrition };
const nutritionFields: { emphasized?: boolean; key: NutritionKey; label: string; unit: string }[] = [
  { key: "energy_kcal", label: "Calorías", unit: "kcal" },
  { emphasized: true, key: "protein_g", label: "Proteínas", unit: "g" },
  { emphasized: true, key: "fat_g", label: "Grasas totales", unit: "g" },
  { key: "saturated_fat_g", label: "Grasas saturadas", unit: "g" },
  { emphasized: true, key: "carbs_g", label: "Carbohidratos", unit: "g" },
  { key: "sugar_g", label: "Azúcares", unit: "g" },
  { key: "fiber_g", label: "Fibra", unit: "g" },
  { key: "sodium_mg", label: "Sodio", unit: "mg" },
];

export function SupplementFormScreen() {
  const { id, returnTo } = useLocalSearchParams<{ id?: string; returnTo?: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const creating = !id || id === "new";
  const returnHref = internalHref(returnTo);
  const [draft, setDraft] = useState<SupplementDraft>(blank);
  const [pro, setPro] = useState(false);
  const [available, setAvailable] = useState(false);
  const [upsell, setUpsell] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formPickerExpanded, setFormPickerExpanded] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (field: keyof SupplementDraft, value: string) => setDraft((current) => ({ ...current, [field]: value }));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      fallback: returnHref ?? "/libraries/supplements" as Href,
      identityVisible: compactHeaderVisible,
      mode: "back",
      title: creating ? "Crear nuevo suplemento" : "Editar suplemento",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, creating, returnHref, setHeaderPresentation]));
  useFocusEffect(useCallback(() => {
    let active = true;
    void (async () => {
      try {
        const entitlements = await apiRequest<EntitlementsData>("/api/v1/entitlements", { cache: "no-store" });
        if (!active) return;
        const allowed = Boolean(entitlements.workspace_features?.can_use_supplements);
        setAvailable(Boolean(entitlements.workspace_features?.supplements_available));
        setPro(allowed);
        if (allowed && !creating) {
          const item = await apiRequest<Supplement>(`/api/v1/library/supplements/${id}`);
          if (active) {
            const { default_unit, ...itemWithoutUnit } = item;
            setDraft({
              ...itemWithoutUnit,
              form: editableSupplementForm(item.form, default_unit),
              default_quantity: item.default_quantity ?? "",
              nutrition: Object.fromEntries(Object.keys(blankNutrition).map((key) => [key, item.nutrition?.[key as NutritionKey] ?? ""])) as NutritionDraft,
            });
          }
        }
      } catch (nextError) { if (active) setError(userFacingError(nextError)); }
      finally { if (active) setLoading(false); }
    })();
    return () => { active = false; };
  }, [apiRequest, creating, id]));

  async function save() {
    if (!draft.name.trim()) { setError("Escribe el nombre del suplemento."); return; }
    const quantity = draft.default_quantity.trim();
    const normalizedQuantity = quantity.replace(",", ".");
    if (!draft.form || !normalizedQuantity || !(Number(normalizedQuantity) > 0)) {
      setError("Selecciona una forma y define una dosis predeterminada válida."); return;
    }
    if (draft.components.some((row) => !row.name.trim() || !(Number(row.quantity) > 0))) {
      setError("Completa el nombre y la cantidad de cada componente."); return;
    }
    const normalizedNutrition = Object.fromEntries(nutritionFields.map(({ key }) => {
      const value = draft.nutrition[key].trim().replace(",", ".");
      return [key, value === "" ? null : value];
    })) as Record<NutritionKey, string | null>;
    if (Object.values(normalizedNutrition).some((value) => value != null && (!Number.isFinite(Number(value)) || Number(value) < 0))) {
      setError("Revisa los valores de la información nutricional."); return;
    }
    setSaving(true); setError(null);
    try {
      const payload = { ...draft, default_unit: defaultUnitForSupplementForm(draft.form), nutrition: normalizedNutrition, default_quantity: normalizedQuantity, components: draft.components.map((row) => ({ ...row, quantity: row.quantity.trim() })) };
      const saved = await apiRequest<Supplement>(creating ? "/api/v1/library/supplements" : `/api/v1/library/supplements/${id}`, { method: creating ? "POST" : "PUT", body: JSON.stringify(payload) });
      if (creating && returnHref) router.dismissTo(returnHref);
      else router.replace(`/libraries/supplements/${saved.id}` as Href);
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setSaving(false); }
  }
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Cargando suplemento…" />;
  const handleScroll = ({ nativeEvent }: NativeSyntheticEvent<NativeScrollEvent>) => setCompactHeaderVisible(isHeaderIdentityVisible(nativeEvent.contentOffset.y));
  return <>
    <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.flex}>
        <ScrollView automaticallyAdjustKeyboardInsets contentContainerStyle={styles.content} keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"} keyboardShouldPersistTaps="handled" onScroll={handleScroll} scrollEventThrottle={16} showsVerticalScrollIndicator={false}>
          <CollectionPageHeader entity="supplement" title={creating ? "Crear nuevo suplemento" : "Editar suplemento"} />
          {!available ? <InlineNotice tone="info">La biblioteca de suplementos aún no está disponible.</InlineNotice> : !pro ? <Button label="Abrir Suplementos Pro" onPress={() => setUpsell(true)} variant="primary" /> : <View style={styles.formBody}>
            <View style={styles.section}>
              <Field autoCapitalize="sentences" label="Nombre" onChangeText={(value) => set("name", value)} placeholder="Ej: Citrato de magnesio" value={draft.name} />
              <Field autoCapitalize="words" label="Marca (opcional)" onChangeText={(value) => set("brand", value)} placeholder="Ej: Marca o laboratorio" value={draft.brand} />
            </View>
            <View style={styles.section}>
              <Field autoCapitalize="sentences" label="Descripción (opcional)" multiline onChangeText={(value) => set("description", value)} placeholder="Información general del suplemento" value={draft.description} />
            </View>
            <View style={styles.section}>
              <View style={styles.sectionHeading}>
                <Text style={styles.heading}>Dosis predeterminada</Text>
                <Text style={styles.helper}>Se usará como punto de partida al agregarlo a una ingesta. La unidad se toma de la forma elegida.</Text>
              </View>
              <SupplementFormPicker label="Forma" onChange={(value) => set("form", value)} onExpandedChange={setFormPickerExpanded} options={[{ label: "Sin definir", value: "" }, ...supplementForms.map((value) => ({ label: unitLabels[value], value }))]} value={draft.form} />
              <Field keyboardType="decimal-pad" label="Cantidad" onChangeText={(value) => set("default_quantity", value)} value={draft.default_quantity} />
            </View>
            <View style={styles.section}>
              <View style={styles.sectionHeading}>
                <Text style={styles.heading}>Información nutricional</Text>
                <Text style={styles.helper}>Valores por dosis predeterminada. Se muestran en la ficha del suplemento y no se suman a la minuta.</Text>
              </View>
              <View style={styles.nutritionRows}>
                {nutritionFields.map((field, index) => <View key={field.key} style={[styles.nutritionRow, index === nutritionFields.length - 1 && styles.nutritionRowLast]}>
                  <Text style={[styles.nutritionLabel, field.emphasized && styles.nutritionLabelEmphasis]}>{field.label}</Text>
                  <View style={styles.nutritionInputSurface}>
                    <TextInput accessibilityLabel={field.label} keyboardType="decimal-pad" onChangeText={(value) => setDraft((current) => ({ ...current, nutrition: { ...current.nutrition, [field.key]: value } }))} selectTextOnFocus style={styles.nutritionInput} value={draft.nutrition[field.key]} />
                    <Text style={styles.nutritionUnit}>{field.unit}</Text>
                  </View>
                </View>)}
              </View>
            </View>
            <View style={styles.section}>
              <View style={styles.sectionHeading}>
                <Text style={styles.heading}>Componentes</Text>
                <Text style={styles.helper}>Opcional. Registra los ingredientes activos y su cantidad.</Text>
              </View>
              {draft.components.map((component, index) => <View key={index} style={styles.component}>
                <Text style={styles.componentTitle}>Componente {index + 1}</Text>
                <Field label="Nombre" onChangeText={(value) => setDraft((current) => ({ ...current, components: current.components.map((row, rowIndex) => rowIndex === index ? { ...row, name: value } : row) }))} value={component.name} />
                <Field keyboardType="decimal-pad" label="Cantidad" onChangeText={(value) => setDraft((current) => ({ ...current, components: current.components.map((row, rowIndex) => rowIndex === index ? { ...row, quantity: value } : row) }))} value={component.quantity} />
                <SupplementChoiceGrid label="Unidad" onChange={(value) => setDraft((current) => ({ ...current, components: current.components.map((row, rowIndex) => rowIndex === index ? { ...row, unit: value } : row) }))} options={componentUnits.map((value) => ({ label: value, value }))} value={component.unit} />
                <Button label="Quitar componente" onPress={() => setDraft((current) => ({ ...current, components: current.components.filter((_, rowIndex) => rowIndex !== index) }))} variant="secondary" />
              </View>)}
              <Button label="+ Agregar componente" onPress={() => setDraft((current) => ({ ...current, components: [...current.components, { name: "", quantity: "", unit: "mg" }] }))} variant="secondary" />
            </View>
            <View style={styles.section}>
              <Field autoCapitalize="sentences" label="Notas personales" multiline onChangeText={(value) => set("user_information", value)} placeholder="Anota aquí información útil para ti" value={draft.user_information} />
            </View>
            {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
            <View style={styles.formSubmit}>
              <Button disabled={!draft.name.trim() || !draft.form || !draft.default_quantity.trim() || formPickerExpanded || saving} label={creating ? "Crear suplemento" : "Guardar cambios"} loading={saving} onPress={() => void save()} variant="primary" />
            </View>
          </View>}
          {!pro && error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
    <SupplementProSheet onClose={() => setUpsell(false)} visible={upsell} />
  </>;
}

const styles = StyleSheet.create({
  component: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.panel, borderWidth: 1, gap: tokens.spacing.md, padding: tokens.card.outerPadding },
  componentTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  content: { flexGrow: 1, gap: tokens.spacing.lg, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  flex: { flex: 1 },
  formBody: { gap: tokens.spacing.xl },
  formSubmit: { gap: tokens.spacing.md, marginTop: tokens.spacing.md },
  heading: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.extraBold },
  helper: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 20 },
  nutritionRows: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, marginTop: -tokens.spacing.xs },
  nutritionRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 46, paddingLeft: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  nutritionRowLast: { borderBottomWidth: 0 },
  nutritionLabel: { color: tokens.color.textMain, flex: 1, fontSize: 14, lineHeight: 20 },
  nutritionLabelEmphasis: { fontWeight: tokens.weight.bold },
  nutritionInputSurface: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, flexDirection: "row", height: 32, minWidth: 112, paddingHorizontal: tokens.spacing.sm },
  nutritionInput: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, height: 30, padding: 0, textAlign: "right" },
  nutritionUnit: { color: tokens.color.textSoft, fontSize: 12, marginLeft: 5 },
  safeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  section: { gap: tokens.spacing.lg },
  sectionHeading: { gap: tokens.spacing.xs },
});
