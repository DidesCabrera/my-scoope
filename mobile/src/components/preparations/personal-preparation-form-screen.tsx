import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Alert, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { PersonalPreparation, PreparationDraft } from "@/api/preparations";
import type { EntitlementsData, FoodPickerOption } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { Button, Card, CollectionPageHeader, InlineNotice, LoadingState, SearchField } from "@/components/ui";
import { Field } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type IngredientDraft = { food_id: number; name: string; quantity_g: string };

export function PersonalPreparationFormScreen() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const creating = !id || id === "new";
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [available, setAvailable] = useState(false);
  const [allowed, setAllowed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [yieldG, setYieldG] = useState("");
  const [portionG, setPortionG] = useState("100");
  const [manualYield, setManualYield] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [isDraft, setIsDraft] = useState(false);
  const [ingredients, setIngredients] = useState<IngredientDraft[]>([]);
  const [search, setSearch] = useState("");
  const [foodOptions, setFoodOptions] = useState<FoodPickerOption[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ mode: "back", fallback: "/libraries/preparations" as Href, title: creating ? "Crear preparación" : isDraft ? "Agregar ingredientes" : "Editar preparación" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [creating, isDraft, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    let active = true;
    void (async () => {
      try {
        const entitlements = await apiRequest<EntitlementsData>("/api/v1/entitlements", { cache: "no-store" });
        if (!active) return;
        const enabled = Boolean(entitlements.workspace_features?.personal_preparations_available);
        const canUse = Boolean(entitlements.workspace_features?.can_use_personal_preparations);
        setAvailable(enabled);
        setAllowed(canUse);
        if (canUse && !creating) {
          const item = await apiRequest<PersonalPreparation>(`/api/v1/preparations/${id}`);
          if (active && item.is_personal) {
            setName(item.name);
            setIsDraft(Boolean(item.is_draft));
            if (!item.is_draft) {
              setManualYield(Boolean(item.yield_is_manual));
              setYieldG(String(item.yield_g));
              setPortionG(String(item.default_portion_g));
              setIngredients(item.recipe_ingredients.map((row) => ({ ...row, quantity_g: String(row.quantity_g) })));
            }
          }
        }
      } catch (failure) { if (active) setError(userFacingError(failure)); }
      finally { if (active) setLoading(false); }
    })();
    return () => { active = false; };
  }, [apiRequest, creating, id]));

  useEffect(() => {
    if (!allowed || search.trim().length < 2) return;
    let active = true;
    const timer = setTimeout(() => {
      setSearching(true);
      void apiRequest<{ items: FoodPickerOption[] }>(`/api/v1/foods?search=${encodeURIComponent(search.trim())}&limit=30`)
        .then((page) => { if (active) setFoodOptions(page.items.filter((food) => food.quantity_unit === "g" && !ingredients.some((row) => row.food_id === food.id))); })
        .catch((failure) => { if (active) setError(userFacingError(failure)); })
        .finally(() => { if (active) setSearching(false); });
    }, 250);
    return () => { active = false; clearTimeout(timer); };
  }, [allowed, apiRequest, ingredients, search]);

  const setQuantity = (foodId: number, value: string) => setIngredients((current) => current.map((row) => row.food_id === foodId ? { ...row, quantity_g: value } : row));
  const addIngredient = (food: FoodPickerOption) => {
    setIngredients((current) => [...current, { food_id: food.id, name: food.display_name, quantity_g: "" }]);
    setSearch("");
    setFoodOptions([]);
    setSearching(false);
  };

  async function save() {
    if (!name.trim()) { setError("Escribe un nombre para la preparación."); return; }
    if (creating) {
      setSaving(true); setError(null);
      try {
        const draft = await apiRequest<PreparationDraft>("/api/v1/library/preparations/drafts", {
          method: "POST", body: JSON.stringify({ name: name.trim() }),
        });
        router.replace(`/libraries/preparations/${draft.id}/edit` as Href);
      } catch (failure) { setError(userFacingError(failure)); }
      finally { setSaving(false); }
      return;
    }
    const yieldAmount = Number(yieldG.trim().replace(",", "."));
    const portionAmount = Number(portionG.trim().replace(",", "."));
    if ((manualYield && (!Number.isFinite(yieldAmount) || yieldAmount <= 0)) || !Number.isFinite(portionAmount) || portionAmount <= 0) {
      setError("Define un rendimiento y una porción válidos en gramos."); return;
    }
    if (!ingredients.length || ingredients.some((row) => !Number.isFinite(Number(row.quantity_g.replace(",", "."))) || Number(row.quantity_g.replace(",", ".")) <= 0)) {
      setError("Agrega al menos un ingrediente y define su cantidad en gramos."); return;
    }
    setSaving(true); setError(null);
    try {
      const saved = await apiRequest<PersonalPreparation>(`/api/v1/library/preparations/${id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: name.trim(), ...(manualYield ? { yield_g: yieldAmount } : {}), default_portion_g: portionAmount,
          ingredients: ingredients.map((row) => ({ food_id: row.food_id, quantity_g: Number(row.quantity_g.replace(",", ".")) })),
        }),
      });
      router.replace(`/libraries/preparations/${saved.id}` as Href);
    } catch (failure) { setError(userFacingError(failure)); }
    finally { setSaving(false); }
  }

  function removeDraft() {
    Alert.alert("Eliminar borrador", `¿Eliminar ${name.trim()} de tus preparaciones?`, [
      { text: "Cancelar", style: "cancel" },
      { text: "Eliminar", style: "destructive", onPress: () => {
        void apiRequest(`/api/v1/library/preparations/${id}`, { method: "DELETE" })
          .then(() => router.replace("/libraries/preparations" as Href))
          .catch((failure) => setError(userFacingError(failure)));
      } },
    ]);
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Cargando preparación…" />;
  return <SafeAreaView edges={["left", "right"]} style={styles.screen}>
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.flex}>
      <ScrollView automaticallyAdjustKeyboardInsets contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        <CollectionPageHeader entity="preparation" title={creating ? "Crear preparación" : isDraft ? "Agregar ingredientes" : "Editar preparación"} />
        {!available ? <InlineNotice tone="info">La biblioteca de preparaciones aún no está disponible.</InlineNotice> : !allowed ? <Card><InlineNotice tone="info">Las preparaciones personales requieren Pro.</InlineNotice><Button label="Conocer Pro" onPress={() => router.push("/subscription" as Href)} /></Card> : <>
          <Card style={styles.section}>
            <Field label="Nombre" onChangeText={setName} placeholder="Ej: Salsa de tomate casera" value={name} />
            {creating ? <Text style={styles.helper}>Después podrás agregar los alimentos de la receta.</Text> : null}
          </Card>
          {!creating ? <><View style={styles.section}>
            <Text style={styles.heading}>Ingredientes</Text>
            {ingredients.map((row) => <Card key={row.food_id} style={styles.ingredient}>
              <Text style={styles.ingredientName}>{row.name}</Text>
              <Field keyboardType="decimal-pad" label="Cantidad en la receta (g)" onChangeText={(value) => setQuantity(row.food_id, value)} value={row.quantity_g} />
              <Button label={`Quitar ${row.name}`} onPress={() => setIngredients((current) => current.filter((item) => item.food_id !== row.food_id))} variant="secondary" />
            </Card>)}
            <SearchField accessibilityLabel="Buscar ingrediente" busy={searching} onChangeText={(value) => { setSearch(value); setFoodOptions([]); setSearching(false); }} onClear={() => { setSearch(""); setFoodOptions([]); setSearching(false); }} placeholder="Buscar alimento para agregar" value={search} />
            {foodOptions.map((food) => <Card key={food.id} style={styles.result}>
              <Text style={styles.ingredientName}>{food.display_name}</Text>
              <Button label={`Agregar ${food.display_name}`} onPress={() => addIngredient(food)} variant="secondary" />
            </Card>)}
            <Text style={styles.helper}>Solo se pueden agregar alimentos con información por gramos. Los alérgenos de una preparación personal quedan sin evaluación.</Text>
          </View>
          <Card style={styles.section}>
            <Text style={styles.helper}>Rendimiento estimado: {ingredients.reduce((sum, row) => sum + (Number(row.quantity_g.replace(",", ".")) || 0), 0)} g, según los alimentos de la receta. Porción habitual: {portionG} g.</Text>
            <Button label={advancedOpen ? "Ocultar opciones avanzadas" : "Opciones avanzadas"} onPress={() => setAdvancedOpen((open) => !open)} variant="secondary" />
            {advancedOpen ? <>
              <Button label={manualYield ? "Usar rendimiento estimado" : "Corregir rendimiento final"} onPress={() => setManualYield((value) => !value)} variant="secondary" />
              {manualYield ? <Field keyboardType="decimal-pad" label="Rendimiento final (g)" onChangeText={setYieldG} placeholder="Ej: 500" value={yieldG} /> : null}
              <Field keyboardType="decimal-pad" label="Porción habitual (g)" onChangeText={setPortionG} value={portionG} />
            </> : null}
          </Card></> : null}
          {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
          <Button disabled={saving} label={creating ? "Crear y continuar" : "Guardar preparación"} loading={saving} onPress={() => void save()} variant="primary" />
          {isDraft ? <Button label="Eliminar borrador" onPress={removeDraft} variant="danger" /> : null}
        </>}
      </ScrollView>
    </KeyboardAvoidingView>
  </SafeAreaView>;
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, gap: tokens.spacing.lg, paddingBottom: 48, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  flex: { flex: 1 },
  heading: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.bold },
  helper: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 20 },
  ingredient: { gap: tokens.spacing.sm },
  ingredientName: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  result: { flexDirection: "row", alignItems: "center", gap: tokens.spacing.md, justifyContent: "space-between" },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  section: { gap: tokens.spacing.md },
});
