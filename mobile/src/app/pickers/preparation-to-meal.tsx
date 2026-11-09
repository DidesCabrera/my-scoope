import { type Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { LibraryItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { tokens } from "@/design/tokens";

type PreparationDetail = {
  id: number; name: string; version: number; household_label: string; default_portion_g: number;
  selected_units: number | null; grams: number; nutrition: { calories: number; protein_g: number; carbs_g: number; fat_g: number; sodium_mg: number | null };
  allergens: string[]; allergen_status: string; evidence: { source_name?: string; source_url?: string; yield_evidence?: string };
  ingredients: { food_id: number; name: string; quantity_g: number; preparation_state: string; is_condiment: boolean }[];
};

export default function PreparationToMealPicker() {
  const { mealId, relationId, preparationId } = useLocalSearchParams<{ mealId?: string; relationId?: string; preparationId?: string }>();
  const meal = Number(mealId);
  const relation = Number(relationId);
  const initialPreparation = Number(preparationId);
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<PreparationDetail[]>([]);
  const [selected, setSelected] = useState<PreparationDetail | null>(null);
  const [mode, setMode] = useState<"units" | "grams">("units");
  const [units, setUnits] = useState(1);
  const [grams, setGrams] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "authenticated") return;
    let active = true;
    void apiRequest<{ items: PreparationDetail[] }>(`/api/v1/preparations?search=${encodeURIComponent(search)}`)
      .then((page) => { if (active) setItems(page.items); })
      .catch((failure) => { if (active) setError(userFacingError(failure)); });
    return () => { active = false; };
  }, [apiRequest, search, status]);
  useEffect(() => {
    if (status !== "authenticated" || !initialPreparation) return;
    void (async () => {
      try {
        const detail = await apiRequest<PreparationDetail>(`/api/v1/preparations/${initialPreparation}`);
        setSelected(detail);
        if (relation) {
          const saved = await apiRequest<LibraryItem>(`/api/v1/library/meals/${meal}`);
          const row = saved.panel.preparations?.find((item) => item.relation_id === relation);
          if (row) {
            setMode(row.selection_mode);
            setUnits(row.selected_units ?? 1);
            setGrams(String(row.quantity_g));
          }
        }
      } catch (failure) { setError(userFacingError(failure)); }
    })();
  }, [apiRequest, initialPreparation, meal, relation, status]);

  const selectedId = selected?.id;
  useEffect(() => {
    if (!selectedId || status !== "authenticated") return;
    const query = mode === "units" ? `units=${units}` : `grams=${encodeURIComponent(grams)}`;
    if (mode === "grams" && !(Number(grams) > 0)) return;
    let active = true;
    void apiRequest<PreparationDetail>(`/api/v1/preparations/${selectedId}?${query}`)
      .then((detail) => { if (active) setSelected(detail); })
      .catch((failure) => { if (active) setError(userFacingError(failure)); });
    return () => { active = false; };
  }, [apiRequest, mode, units, grams, selectedId, status]);

  async function save() {
    if (!selected || busy) return;
    setBusy(true); setError(null);
    try {
      const payload = mode === "units" ? { units, grams: null } : { units: null, grams: Number(grams) };
      const url = relation
        ? `/api/v1/library/meals/${meal}/preparations/${relation}`
        : `/api/v1/library/meals/${meal}/preparations`;
      await apiRequest(url, { method: relation ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(relation ? payload : { preparation_id: selected.id, ...payload }) });
      router.dismissTo(`/libraries/meals/${meal}` as Href);
    } catch (failure) { setError(userFacingError(failure)); }
    finally { setBusy(false); }
  }

  if (!Number.isInteger(meal) || meal <= 0) return <Redirect href="/libraries/meals" />;
  if (status === "anonymous") return <Redirect href="/login" />;
  return <SafeAreaView style={styles.screen}><ScrollView contentContainerStyle={styles.content}>
    <Text style={styles.title}>Agregar preparación</Text>
    {!relation ? <><TextInput accessibilityLabel="Buscar preparación" onChangeText={setSearch} placeholder="Buscar preparación" style={styles.input} value={search} />
      {items.map((item) => <Pressable key={item.id} onPress={() => { setSelected(item); setMode("units"); setUnits(1); setGrams(""); }} style={styles.row}><Text style={styles.name}>{item.name}</Text><Text style={styles.body}>{item.default_portion_g} g por {item.household_label}</Text></Pressable>)}
      {!items.length ? <Text style={styles.body}>No hay preparaciones publicadas con ese nombre.</Text> : null}</> : null}
    {selected ? <View style={styles.detail}><Text style={styles.name}>{selected.name} · revisión {selected.version}</Text>
      <Text style={styles.body}>{selected.grams} g · {selected.nutrition.calories} kcal · Proteína {selected.nutrition.protein_g} g · Carbohidratos {selected.nutrition.carbs_g} g · Grasa {selected.nutrition.fat_g} g</Text>
      <Text style={styles.body}>Sodio: {selected.nutrition.sodium_mg ?? "sin dato"} mg · Alérgenos: {selected.allergens.length ? selected.allergens.join(", ") : "ninguno confirmado"}</Text>
      <View style={styles.controls}><Pressable onPress={() => setMode("units")}><Text style={styles.link}>Unidades</Text></Pressable><Pressable onPress={() => { setMode("grams"); setGrams(String(selected.grams)); }}><Text style={styles.link}>Gramos</Text></Pressable></View>
      {mode === "units" ? <View style={styles.controls}><Pressable onPress={() => setUnits(Math.max(0.5, units - 0.5))}><Text style={styles.link}>−</Text></Pressable><Text style={styles.body}>{units} {selected.household_label}</Text><Pressable onPress={() => setUnits(Math.min(10, units + 0.5))}><Text style={styles.link}>+</Text></Pressable></View> : <TextInput accessibilityLabel="Cantidad en gramos" keyboardType="decimal-pad" onChangeText={setGrams} style={styles.input} value={grams} />}
      <Text style={styles.name}>Ingredientes para esta porción</Text>
      {selected.ingredients.map((ingredient, index) => <Pressable key={`${ingredient.food_id}:${index}`} onPress={() => router.push(`/libraries/foods/${ingredient.food_id}` as Href)} style={styles.row}><Text style={styles.body}>{ingredient.name} · {ingredient.quantity_g} g · {ingredient.preparation_state}{ingredient.is_condiment ? " · condimento" : ""} ›</Text></Pressable>)}
      <Text style={styles.body}>Fuente: {selected.evidence.source_name || "Sin fuente"}. Rendimiento: {selected.evidence.yield_evidence || "Sin evidencia"}</Text>
      <Pressable disabled={busy} onPress={() => void save()} style={styles.action}><Text style={styles.actionText}>{busy ? "Guardando…" : relation ? "Actualizar porción" : "Agregar a la comida"}</Text></Pressable>
    </View> : null}
    {error ? <Text style={styles.error}>{error}</Text> : null}
  </ScrollView></SafeAreaView>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: tokens.color.surfaceApp },
  content: { padding: 20, gap: 14 },
  title: { color: tokens.color.textMain, fontSize: 24, fontWeight: "700" },
  name: { color: tokens.color.textMain, fontSize: 17, fontWeight: "700" },
  input: { borderWidth: 1, borderColor: tokens.color.borderDefault, borderRadius: 10, padding: 12, color: tokens.color.textMain },
  body: { color: tokens.color.textMain },
  row: { padding: 12, borderRadius: 10, borderWidth: 1, borderColor: tokens.color.textMain, gap: 3 },
  detail: { gap: 14 },
  controls: { flexDirection: "row", alignItems: "center", justifyContent: "space-around", padding: 12 },
  link: { color: tokens.color.textMain, fontWeight: "700", fontSize: 18 },
  action: { padding: 15, borderRadius: 10, backgroundColor: tokens.color.interactivePrimary, alignItems: "center" },
  actionText: { color: tokens.color.surfaceApp, fontWeight: "700" },
  error: { color: "#b00020" },
});
