import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { LibraryEntity, LibraryItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { Button, Card, Field, InlineNotice, textStyles } from "@/components/ui/primitives";
import { EntityIcon } from "@/components/ui";
import { tokens } from "@/design/tokens";

type CreatableEntity = LibraryEntity;

type CreateConfig = {
  endpoint: string;
  headerTitle: string;
  identityLabel: string;
  namePlaceholder: string;
  segment: "foods" | "meals" | "daily-plans" | "programs";
  submitLabel: string;
  guidance?: string;
};

const configs: Record<CreatableEntity, CreateConfig> = {
  food: {
    endpoint: "/api/v1/library/foods",
    headerTitle: "Crear alimento",
    identityLabel: "Nuevo alimento",
    namePlaceholder: "Ej: Yogur natural",
    segment: "foods",
    submitLabel: "Crear alimento",
  },
  meal: {
    endpoint: "/api/v1/library/meals",
    guidance: "Después podrás agregar los alimentos y configurar sus porciones.",
    headerTitle: "Crear comida",
    identityLabel: "Nueva comida",
    namePlaceholder: "Según ingredientes, propósito u otro",
    segment: "meals",
    submitLabel: "Crear y continuar",
  },
  dailyPlan: {
    endpoint: "/api/v1/library/daily-plans",
    guidance: "Después podrás agregar las comidas y elegir sus horarios.",
    headerTitle: "Crear plan diario",
    identityLabel: "Nuevo plan diario",
    namePlaceholder: "Un día, objetivo o tipo de jornada",
    segment: "daily-plans",
    submitLabel: "Crear y continuar",
  },
  program: {
    endpoint: "/api/v1/library/programs",
    guidance: "El programa comenzará con una semana. Después podrás asignar planes diarios o agregar más semanas.",
    headerTitle: "Crear programa",
    identityLabel: "Nuevo programa",
    namePlaceholder: "Ej: Volumen controlado",
    segment: "programs",
    submitLabel: "Crear y continuar",
  },
};

function macroNumber(value: string): number | null {
  const normalized = value.trim().replace(",", ".");
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) && parsed >= 0 && parsed <= 100 ? parsed : null;
}

export function LibraryCreateScreen() {
  const params = useLocalSearchParams<{ entity?: string }>();
  const entity = typeof params.entity === "string" && Object.prototype.hasOwnProperty.call(configs, params.entity)
    ? params.entity as CreatableEntity
    : null;
  const config = entity ? configs[entity] : null;
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [name, setName] = useState("");
  const [protein, setProtein] = useState("");
  const [carbs, setCarbs] = useState("");
  const [fat, setFat] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cancel = useCallback(() => {
    if (router.canGoBack()) router.back();
    else if (config) router.replace(`/libraries/${config.segment}` as Href);
  }, [config, router]);

  useFocusEffect(useCallback(() => {
    if (!config) return;
    setHeaderPresentation({
      mode: "back",
      action: { label: "Cancelar", onPress: cancel },
      fallback: `/libraries/${config.segment}` as Href,
      title: config.headerTitle,
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [cancel, config, setHeaderPresentation]));

  const macroValues = useMemo(() => ({
    carbs: macroNumber(carbs),
    fat: macroNumber(fat),
    protein: macroNumber(protein),
  }), [carbs, fat, protein]);
  const cleanName = name.trim();
  const validFood = entity !== "food" || Object.values(macroValues).every((value) => value !== null);
  const canSubmit = Boolean(cleanName && cleanName.length <= 100 && validFood && !submitting);

  async function submit() {
    if (!config || !entity || !canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const body = entity === "food"
        ? { name: cleanName, protein: macroValues.protein, carbs: macroValues.carbs, fat: macroValues.fat }
        : { name: cleanName };
      const created = await apiRequest<LibraryItem>(config.endpoint, {
        body: JSON.stringify(body),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      router.replace(`/libraries/${config.segment}/${created.id}` as Href);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (!config || !entity) return <Redirect href="/today" />;

  return (
    <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <Card accent={tokens.color[entity]} style={styles.formCard}>
            <View style={styles.identityRow}>
              <EntityIcon entity={entity} size="compact" />
              <Text style={styles.eyebrow}>{config.identityLabel}</Text>
            </View>
            <Field autoCapitalize="sentences" label="Nombre" onChangeText={setName} placeholder={config.namePlaceholder} value={name} />
            {entity === "food" ? (
              <View style={styles.macroFields}>
                <View style={styles.macroHeading}>
                  <Text style={styles.macroTitle}>Información por 100 g</Text>
                  <Text style={textStyles.caption}>Ingresa cada macronutriente entre 0 y 100 g.</Text>
                </View>
                <Field keyboardType="decimal-pad" label="Proteínas (g)" onChangeText={setProtein} placeholder="0" value={protein} />
                <Field keyboardType="decimal-pad" label="Carbohidratos (g)" onChangeText={setCarbs} placeholder="0" value={carbs} />
                <Field keyboardType="decimal-pad" label="Grasas (g)" onChangeText={setFat} placeholder="0" value={fat} />
              </View>
            ) : null}
            {config.guidance ? <InlineNotice>{config.guidance}</InlineNotice> : null}
            {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
            <Button disabled={!canSubmit} label={config.submitLabel} loading={submitting} onPress={() => void submit()} />
          </Card>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  flex: { flex: 1 },
  content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.sm },
  formCard: { gap: tokens.spacing.lg },
  identityRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  eyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, textTransform: "uppercase" },
  macroFields: { gap: tokens.spacing.md },
  macroHeading: { gap: tokens.spacing.xs },
  macroTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
});
