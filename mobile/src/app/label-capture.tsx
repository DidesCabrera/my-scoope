import * as Crypto from "expo-crypto";
import { CameraView, useCameraPermissions } from "expo-camera";
import { File } from "expo-file-system";
import { Redirect, useRouter } from "expo-router";
import { useRef, useState } from "react";
import { Platform, StyleSheet, Text, View } from "react-native";

import type { FoodLabelCaptureInput, FoodLabelCaptureResult } from "@/api/types";
import { userFacingError } from "@/api/errors";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, Field, InlineNotice, Pill, Screen, SectionTitle, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { normalizeNutritionLabel, type NutritionLabelDraft } from "@/label-capture/normalize";
import {
  isNutritionLabelOcrAvailable,
  recognizeNutritionLabel,
} from "../../modules/nutrition-label-ocr/src/NutritionLabelOcrModule";

type Phase = "intro" | "camera" | "review" | "saved";
type FormState = {
  name: string;
  energy: string;
  protein: string;
  carbs: string;
  fat: string;
  saturatedFat: string;
  sugar: string;
  fiber: string;
  sodium: string;
  servingSize: string;
};

const emptyForm: FormState = {
  name: "",
  energy: "",
  protein: "",
  carbs: "",
  fat: "",
  saturatedFat: "",
  sugar: "",
  fiber: "",
  sodium: "",
  servingSize: "",
};

const warningCopy: Record<string, string> = {
  manual_review: "Los valores serán ingresados y revisados manualmente.",
  basis_not_detected: "No se identificó si la tabla está expresada por 100 g o por porción.",
  serving_size_required: "Se detectó una porción, pero no su peso en gramos.",
  basis_normalized_from_serving: "Los valores fueron convertidos desde una porción hacia 100 g.",
  energy_macro_mismatch: "Las calorías declaradas difieren del cálculo de proteínas, carbos y grasas.",
  protein_g_missing: "No se detectaron proteínas.",
  carbs_g_missing: "No se detectaron carbos.",
  fat_g_missing: "No se detectaron grasas.",
};

function valueString(value: number | undefined | null): string {
  return value == null ? "" : String(value);
}

function optionalNumber(value: string): number | undefined {
  const clean = value.trim().replace(",", ".");
  if (!clean) return undefined;
  const parsed = Number(clean);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined;
}

function displayWarning(value: string): string {
  if (warningCopy[value]) return warningCopy[value];
  if (value.endsWith("_low_confidence")) return "Un valor tiene baja confianza de lectura y necesita revisión.";
  if (value.endsWith("_outside_expected_range")) return "Un valor quedó fuera del rango nutricional esperado.";
  return value;
}

export default function LabelCaptureScreen() {
  const router = useRouter();
  const cameraRef = useRef<CameraView>(null);
  const { status, apiRequest } = useSession();
  const [permission, requestPermission] = useCameraPermissions();
  const [phase, setPhase] = useState<Phase>("intro");
  const [cameraReady, setCameraReady] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [draft, setDraft] = useState<NutritionLabelDraft | null>(null);
  const [saved, setSaved] = useState<FoodLabelCaptureResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [captureKey, setCaptureKey] = useState(Crypto.randomUUID());

  if (status === "anonymous") return <Redirect href="/login" />;

  function update(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function applyDraft(next: NutritionLabelDraft) {
    setDraft(next);
    setForm({
      ...emptyForm,
      energy: valueString(next.values.energy_kcal),
      protein: valueString(next.values.protein_g),
      carbs: valueString(next.values.carbs_g),
      fat: valueString(next.values.fat_g),
      saturatedFat: valueString(next.values.saturated_fat_g),
      sugar: valueString(next.values.sugar_g),
      fiber: valueString(next.values.fiber_g),
      sodium: valueString(next.values.sodium_mg),
      servingSize: valueString(next.servingSizeG),
    });
    setPhase("review");
  }

  function beginManualReview(message?: string) {
    setDraft({
      basis: "manual",
      servingSizeG: null,
      values: {},
      fieldConfidence: {},
      warnings: ["manual_review"],
      ocrEngine: "manual_entry",
      ocrEngineVersion: "1",
    });
    setForm(emptyForm);
    setError(message ?? null);
    setPhase("review");
  }

  async function beginCamera() {
    setError(null);
    if (Platform.OS !== "ios" || !isNutritionLabelOcrAvailable()) {
      beginManualReview("El OCR local requiere el development build iOS de CML05. Puedes revisar los valores manualmente.");
      return;
    }
    if (!(await CameraView.isAvailableAsync())) {
      beginManualReview("Este dispositivo no tiene una cámara disponible. Puedes ingresar la etiqueta manualmente.");
      return;
    }
    const nextPermission = permission?.granted ? permission : await requestPermission();
    if (!nextPermission.granted) {
      beginManualReview("Sin permiso de cámara, My Scoope continúa con ingreso manual.");
      return;
    }
    setCameraReady(false);
    setPhase("camera");
  }

  async function capture() {
    if (!cameraRef.current || !cameraReady) return;
    setProcessing(true);
    setError(null);
    let photoUri: string | null = null;
    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 0.92, skipProcessing: false });
      photoUri = photo.uri;
      const recognition = await recognizeNutritionLabel(photo.uri);
      applyDraft(normalizeNutritionLabel(recognition));
    } catch (nextError) {
      beginManualReview(`No pudimos leer esta foto. ${userFacingError(nextError)} Puedes completar los valores manualmente.`);
    } finally {
      if (photoUri?.startsWith("file:")) {
        try {
          new File(photoUri).delete();
        } catch {
          // Expo's cache remains ephemeral if the platform has already removed the file.
        }
      }
      setProcessing(false);
    }
  }

  async function save() {
    const protein = optionalNumber(form.protein);
    const carbs = optionalNumber(form.carbs);
    const fat = optionalNumber(form.fat);
    if (!form.name.trim() || protein === undefined || carbs === undefined || fat === undefined) {
      setError("Completa el nombre, proteínas, carbos y grasas antes de confirmar.");
      return;
    }
    const optionalInputs = [form.energy, form.saturatedFat, form.sugar, form.fiber, form.sodium, form.servingSize];
    if (optionalInputs.some((value) => value.trim() && optionalNumber(value) === undefined)) {
      setError("Revisa los campos opcionales: usa sólo números positivos o déjalos vacíos.");
      return;
    }
    if (form.servingSize.trim() && optionalNumber(form.servingSize) === 0) {
      setError("El tamaño de porción debe ser mayor que cero.");
      return;
    }
    const payload: FoodLabelCaptureInput = {
      name: form.name.trim(),
      protein_g: protein,
      carbs_g: carbs,
      fat_g: fat,
      saturated_fat_g: optionalNumber(form.saturatedFat),
      sugar_g: optionalNumber(form.sugar),
      fiber_g: optionalNumber(form.fiber),
      sodium_mg: optionalNumber(form.sodium),
      serving_size_g: optionalNumber(form.servingSize),
      declared_energy_kcal_per_100g: optionalNumber(form.energy),
      detected_basis: draft?.basis ?? "manual",
      ocr_engine: draft?.ocrEngine ?? "manual_entry",
      ocr_engine_version: draft?.ocrEngineVersion ?? "1",
      field_confidence: draft?.fieldConfidence ?? {},
      warnings: draft?.warnings ?? ["manual_review"],
      idempotency_key: captureKey,
    };
    setSaving(true);
    setError(null);
    try {
      setSaved(await apiRequest<FoodLabelCaptureResult>("/api/v1/foods/label-captures", {
        method: "POST",
        body: JSON.stringify(payload),
      }));
      setPhase("saved");
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  }

  function restart() {
    setForm(emptyForm);
    setDraft(null);
    setSaved(null);
    setError(null);
    setCaptureKey(Crypto.randomUUID());
    setPhase("intro");
  }

  if (phase === "camera") {
    return (
      <Screen scroll={false}>
        <AppHeader eyebrow="OCR local" title="Encuadra la tabla" />
        <View style={styles.cameraFrame}>
          <CameraView
            autofocus="off"
            facing="back"
            mode="picture"
            onCameraReady={() => setCameraReady(true)}
            ref={cameraRef}
            style={StyleSheet.absoluteFill}
          />
          <View pointerEvents="none" style={styles.guide} />
          <View pointerEvents="none" style={styles.cameraCopy}>
            <Text style={styles.cameraCopyText}>Evita reflejos y llena el marco con la información nutricional.</Text>
          </View>
        </View>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <Button disabled={!cameraReady} label="Capturar y leer" loading={processing} onPress={() => void capture()} />
        <Button disabled={processing} label="Cancelar" onPress={() => setPhase("intro")} variant="secondary" />
      </Screen>
    );
  }

  return (
    <Screen>
      <AppHeader eyebrow="Alimento privado" title="Digitalizar etiqueta" />
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}

      {phase === "intro" ? (
        <>
          <Card accent={tokens.color.food}>
            <SectionTitle detail="Sin subir la foto" title="Apunta, revisa, confirma" />
            <Text style={textStyles.muted}>La cámara lee la tabla en tu iPhone. Nada se guarda en tu cuenta hasta que revises y confirmes los valores por 100 g.</Text>
            <View style={styles.steps}>
              <Text style={textStyles.caption}>1 · Encuadra sólo la tabla nutricional.</Text>
              <Text style={textStyles.caption}>2 · Revisa los campos dudosos o faltantes.</Text>
              <Text style={textStyles.caption}>3 · Confirma para crear un alimento visible sólo para ti.</Text>
            </View>
          </Card>
          <Button label="Abrir cámara" onPress={() => void beginCamera()} />
          <Button label="Ingresar sin cámara" onPress={() => beginManualReview()} variant="secondary" />
        </>
      ) : null}

      {phase === "review" ? (
        <>
          <InlineNotice tone="warning">El OCR es una ayuda, no una fuente de verdad. Compara cada valor con la etiqueta antes de guardar.</InlineNotice>
          {draft?.warnings.length ? (
            <Card muted>
              <SectionTitle detail={`${draft.warnings.length}`} title="Puntos por revisar" />
              {draft.warnings.map((warning) => <Text key={warning} style={textStyles.caption}>• {displayWarning(warning)}</Text>)}
            </Card>
          ) : <InlineNotice>Lectura clara. Aun así, confirma los valores contra la etiqueta.</InlineNotice>}
          <Card accent={tokens.color.food}>
            <View style={styles.reviewHeader}>
              <Text style={styles.reviewTitle}>Valores por 100 g</Text>
              <Pill color={tokens.color.food} label={draft?.ocrEngine === "apple_vision" ? "OCR local" : "Manual"} />
            </View>
            <Field autoCapitalize="words" label="Nombre del producto" onChangeText={(value) => update("name", value)} placeholder="Ej. Yogur griego natural" value={form.name} />
            <View style={styles.fieldRow}>
              <View style={styles.fieldCell}><Field keyboardType="decimal-pad" label="Proteínas (g)" onChangeText={(value) => update("protein", value)} value={form.protein} /></View>
              <View style={styles.fieldCell}><Field keyboardType="decimal-pad" label="Carbos (g)" onChangeText={(value) => update("carbs", value)} value={form.carbs} /></View>
            </View>
            <View style={styles.fieldRow}>
              <View style={styles.fieldCell}><Field keyboardType="decimal-pad" label="Grasas (g)" onChangeText={(value) => update("fat", value)} value={form.fat} /></View>
              <View style={styles.fieldCell}><Field keyboardType="decimal-pad" label="Energía (kcal)" onChangeText={(value) => update("energy", value)} value={form.energy} /></View>
            </View>
            <View style={styles.fieldRow}>
              <View style={styles.fieldCell}><Field keyboardType="decimal-pad" label="Azúcares (g)" onChangeText={(value) => update("sugar", value)} value={form.sugar} /></View>
              <View style={styles.fieldCell}><Field keyboardType="decimal-pad" label="Fibra (g)" onChangeText={(value) => update("fiber", value)} value={form.fiber} /></View>
            </View>
            <View style={styles.fieldRow}>
              <View style={styles.fieldCell}><Field keyboardType="decimal-pad" label="Grasas saturadas (g)" onChangeText={(value) => update("saturatedFat", value)} value={form.saturatedFat} /></View>
              <View style={styles.fieldCell}><Field keyboardType="decimal-pad" label="Sodio (mg)" onChangeText={(value) => update("sodium", value)} value={form.sodium} /></View>
            </View>
            <Field keyboardType="decimal-pad" label="Tamaño de porción original (g, opcional)" onChangeText={(value) => update("servingSize", value)} value={form.servingSize} />
            <Button label="Confirmar y crear alimento" loading={saving} onPress={() => void save()} />
          </Card>
          <Button disabled={saving} label="Volver a capturar" onPress={() => setPhase("intro")} variant="secondary" />
        </>
      ) : null}

      {phase === "saved" && saved ? (
        <>
          <Card accent={tokens.color.success}>
            <SectionTitle detail={`${Math.round(saved.total_kcal)} kcal`} title={saved.name} />
            <Text style={textStyles.muted}>Creado en tu biblioteca privada · P {saved.protein_g} g · C {saved.carbs_g} g · G {saved.fat_g} g</Text>
            <Text style={textStyles.caption}>La foto y el texto OCR no se enviaron. Sólo se guardaron los valores que confirmaste y un recibo técnico sin contenido crudo.</Text>
          </Card>
          <Button label="Digitalizar otra etiqueta" onPress={restart} />
        </>
      ) : null}

      <Button label="Volver a Today" onPress={() => router.back()} variant="secondary" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  cameraFrame: { borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.card, borderWidth: 1, flex: 1, minHeight: 420, overflow: "hidden" },
  guide: { borderColor: tokens.color.food, borderRadius: tokens.radius.lg, borderWidth: 3, bottom: 70, left: 24, position: "absolute", right: 24, top: 52 },
  cameraCopy: { backgroundColor: "rgba(0,0,0,0.72)", bottom: 0, left: 0, padding: 16, position: "absolute", right: 0 },
  cameraCopyText: { color: tokens.color.textMain, fontSize: 13, lineHeight: 18, textAlign: "center" },
  steps: { gap: tokens.spacing.sm },
  reviewHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  reviewTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: "800" },
  fieldRow: { flexDirection: "row", gap: tokens.spacing.sm },
  fieldCell: { flex: 1 },
});
