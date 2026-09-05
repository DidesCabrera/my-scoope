import * as Crypto from "expo-crypto";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import { Redirect, useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Platform, StyleSheet, Switch, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, Field, InlineNotice, Pill, Screen, SectionTitle, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { deleteCachedImage, prepareLabelImage, type PreparedLabelImage } from "@/label-capture/image";
import {
  confirmNutritionLabelBasis,
  convertServingDraftTo100g,
  convertVolumeDraftTo100g,
  normalizeNutritionLabel,
  type NutritionField,
  type NutritionLabelDraft,
} from "@/label-capture/normalize";
import type {
  FoodLabelAIAnalysis,
  FoodLabelAIConfig,
  FoodLabelCaptureInput,
  FoodLabelCaptureResult,
} from "@/label-capture/types";
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
  volumeWeight: string;
};

const emptyForm: FormState = {
  name: "", energy: "", protein: "", carbs: "", fat: "", saturatedFat: "",
  sugar: "", fiber: "", sodium: "", servingSize: "", volumeWeight: "",
};

const warningCopy: Record<string, string> = {
  manual_review: "Los valores serán ingresados y revisados manualmente.",
  basis_normalized_from_serving: "La IA convirtió los valores desde una porción hacia 100 g.",
  basis_per_100ml_requires_weight: "La etiqueta está expresada por 100 ml. Indica cuánto pesan 100 ml para convertirla con precisión.",
  basis_normalized_from_100ml: "Los valores fueron convertidos de 100 ml a 100 g usando el peso que indicaste.",
  basis_not_detected: "Confirma si los valores corresponden a 100 g, 100 ml o una porción.",
  serving_size_required: "Indica el peso en gramos de la porción impresa.",
  energy_macro_mismatch: "Las calorías declaradas difieren del cálculo de proteínas, carbos y grasas.",
  model_escalation_unresolved: "La lectura requirió comprobaciones adicionales. Revisa con especial atención.",
};

function valueString(value: number | undefined | null) {
  return value == null ? "" : String(value);
}

function optionalNumber(value: string): number | undefined {
  const clean = value.trim().replace(",", ".");
  if (!clean) return undefined;
  const parsed = Number(clean);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined;
}

function displayWarning(value: string) {
  return warningCopy[value] ?? "Compara este valor con la etiqueta antes de confirmar.";
}

function aiDraft(result: FoodLabelAIAnalysis): NutritionLabelDraft {
  return {
    basis: result.basis === "unknown" ? "manual" : result.basis,
    servingSizeG: result.serving_size_g,
    sourceValues: result.source_values as Partial<Record<NutritionField, number>>,
    values: result.values as Partial<Record<NutritionField, number>>,
    fieldConfidence: result.field_confidence,
    warnings: result.warnings,
    normalizationStatus: result.normalization_status,
    ocrEngine: result.ocr_engine,
    ocrEngineVersion: result.ocr_engine_version,
  };
}

export default function LabelCaptureScreen() {
  const router = useRouter();
  const cameraRef = useRef<CameraView>(null);
  const { status, apiRequest } = useSession();
  const [permission, requestPermission] = useCameraPermissions();
  const [phase, setPhase] = useState<Phase>("intro");
  const [cameraReady, setCameraReady] = useState(false);
  const [openingCamera, setOpeningCamera] = useState(false);
  const [torchEnabled, setTorchEnabled] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [draft, setDraft] = useState<NutritionLabelDraft | null>(null);
  const [saved, setSaved] = useState<FoodLabelCaptureResult | null>(null);
  const [config, setConfig] = useState<FoodLabelAIConfig | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [prepared, setPrepared] = useState<PreparedLabelImage | null>(null);
  const [retainImage, setRetainImage] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [captureKey, setCaptureKey] = useState(Crypto.randomUUID());

  useEffect(() => {
    if (status !== "authenticated") return;
    void apiRequest<FoodLabelAIConfig>("/api/v1/foods/label-captures/config")
      .then(setConfig)
      .catch(() => setConfig(null));
  }, [apiRequest, status]);

  useEffect(() => () => deleteCachedImage(prepared?.uri), [prepared?.uri]);

  if (status === "anonymous") return <Redirect href="/login" />;

  function update(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function applyDraft(next: NutritionLabelDraft, name = "") {
    setDraft(next);
    const displayedValues = next.normalizationStatus === "ready" ? next.values : next.sourceValues;
    setForm({
      ...emptyForm,
      name,
      energy: valueString(displayedValues.energy_kcal),
      protein: valueString(displayedValues.protein_g),
      carbs: valueString(displayedValues.carbs_g),
      fat: valueString(displayedValues.fat_g),
      saturatedFat: valueString(displayedValues.saturated_fat_g),
      sugar: valueString(displayedValues.sugar_g),
      fiber: valueString(displayedValues.fiber_g),
      sodium: valueString(displayedValues.sodium_mg),
      servingSize: valueString(next.servingSizeG),
    });
    setPhase("review");
  }

  function confirmBasis(basis: "per_100g" | "per_serving" | "per_100ml") {
    if (!draft) return;
    try {
      applyDraft(confirmNutritionLabelBasis(draft, basis), form.name);
      setError(null);
    } catch {
      setError("No pudimos confirmar la base de esta etiqueta.");
    }
  }

  function normalizeServingValues() {
    const servingSize = optionalNumber(form.servingSize);
    if (!draft || !servingSize || servingSize <= 0) {
      setError("Indica el peso en gramos de la porción impresa.");
      return;
    }
    try {
      applyDraft(convertServingDraftTo100g(draft, servingSize), form.name);
      setError(null);
    } catch {
      setError("No pudimos convertir los valores de esta porción.");
    }
  }

  function normalizeVolumeValues() {
    const weight = optionalNumber(form.volumeWeight);
    if (!draft || !weight || weight <= 0) {
      setError("Indica cuántos gramos pesan 100 ml de este producto.");
      return;
    }
    try {
      const next = convertVolumeDraftTo100g(draft, weight);
      applyDraft(next, form.name);
      setForm((current) => ({ ...current, volumeWeight: String(weight) }));
      setError(null);
    } catch {
      setError("No pudimos convertir los valores expresados por 100 ml.");
    }
  }

  function beginManualReview(message?: string) {
    deleteCachedImage(prepared?.uri);
    setPrepared(null);
    setAnalysisId(null);
    setRetainImage(false);
    applyDraft({
      basis: "manual",
      servingSizeG: null,
      sourceValues: {},
      values: {},
      fieldConfidence: {},
      warnings: ["manual_review"],
      normalizationStatus: "ready",
      ocrEngine: "manual_entry",
      ocrEngineVersion: "1",
    });
    setError(message ?? null);
  }

  async function beginCamera() {
    if (openingCamera) return;
    setOpeningCamera(true);
    setError(null);
    setTorchEnabled(false);
    try {
      const nextPermission = permission?.granted ? permission : await requestPermission();
      if (!nextPermission.granted) {
        setError("Sin permiso de cámara aún puedes elegir una foto o ingresar los valores manualmente.");
        return;
      }
      setCameraReady(false);
      setPhase("camera");
    } catch {
      setError("No pudimos abrir la cámara. Reintenta o selecciona una foto.");
    } finally {
      setOpeningCamera(false);
    }
  }

  async function processImage(uri: string, width: number, height: number) {
    setProcessing(true);
    setError(null);
    let nextPrepared: PreparedLabelImage | null = null;
    try {
      nextPrepared = await prepareLabelImage(uri, width, height);
      let localCandidate: { basis: string; values: Record<string, number> } | undefined;
      if (Platform.OS === "ios" && isNutritionLabelOcrAvailable()) {
        try {
          const local = normalizeNutritionLabel(await recognizeNutritionLabel(nextPrepared.uri));
          localCandidate = { basis: local.basis, values: local.values as Record<string, number> };
        } catch {
          // Local OCR is only a quality signal; server-side AI remains authoritative.
        }
      }
      const result = await apiRequest<FoodLabelAIAnalysis>("/api/v1/foods/label-captures/analyze", {
        method: "POST",
        body: JSON.stringify({
          image_base64: nextPrepared.base64,
          image_content_type: nextPrepared.contentType,
          image_width: nextPrepared.width,
          image_height: nextPrepared.height,
          idempotency_key: captureKey,
          consent_to_ai_processing: true,
          local_candidate: localCandidate,
        }),
      });
      setAnalysisId(result.analysis_id);
      setPrepared(nextPrepared);
      setConfig((current) => current ? { ...current, available_credits: result.available_credits } : current);
      applyDraft(aiDraft(result), result.name);
    } catch (nextError) {
      deleteCachedImage(nextPrepared?.uri);
      beginManualReview(`${userFacingError(nextError)} Puedes completar los valores manualmente sin consumir una digitalización fallida.`);
    } finally {
      deleteCachedImage(uri);
      setProcessing(false);
    }
  }

  async function capture() {
    if (!cameraRef.current || !cameraReady || processing) return;
    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 1, skipProcessing: false });
      await processImage(photo.uri, photo.width, photo.height);
    } catch (nextError) {
      beginManualReview(`No pudimos preparar esta foto. ${userFacingError(nextError)}`);
      setProcessing(false);
    }
  }

  async function chooseFromGallery() {
    setProcessing(true);
    setError(null);
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        allowsEditing: false,
        base64: false,
        exif: false,
        quality: 1,
        selectionLimit: 1,
      });
      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        await processImage(asset.uri, asset.width, asset.height);
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setProcessing(false);
    }
  }

  async function save() {
    if (draft?.normalizationStatus !== "ready") {
      setError("Confirma la base y completa la conversión antes de guardar el alimento.");
      return;
    }
    const protein = optionalNumber(form.protein);
    const carbs = optionalNumber(form.carbs);
    const fat = optionalNumber(form.fat);
    if (!form.name.trim() || protein === undefined || carbs === undefined || fat === undefined) {
      setError("Completa el nombre, proteínas, carbos y grasas antes de confirmar.");
      return;
    }
    const optionalInputs = [form.energy, form.saturatedFat, form.sugar, form.fiber, form.sodium, form.servingSize, form.volumeWeight];
    if (optionalInputs.some((value) => value.trim() && optionalNumber(value) === undefined)) {
      setError("Revisa los campos opcionales: usa sólo números positivos o déjalos vacíos.");
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
      volume_weight_g_per_100ml: draft?.basis === "per_100ml" ? optionalNumber(form.volumeWeight) : undefined,
      declared_energy_kcal_per_100g: optionalNumber(form.energy),
      detected_basis: draft?.basis ?? "manual",
      ocr_engine: draft?.ocrEngine ?? "manual_entry",
      ocr_engine_version: draft?.ocrEngineVersion ?? "1",
      field_confidence: draft?.fieldConfidence ?? {},
      warnings: draft?.warnings ?? ["manual_review"],
      idempotency_key: captureKey,
      analysis_id: analysisId ?? undefined,
      retain_label_image: Boolean(retainImage && prepared && analysisId),
      label_image_base64: retainImage ? prepared?.base64 : undefined,
      label_image_content_type: retainImage ? prepared?.contentType : undefined,
    };
    setSaving(true);
    setError(null);
    try {
      const result = await apiRequest<FoodLabelCaptureResult>("/api/v1/foods/label-captures", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setSaved(result);
      deleteCachedImage(prepared?.uri);
      setPrepared(null);
      setPhase("saved");
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  }

  function restart() {
    deleteCachedImage(prepared?.uri);
    setForm(emptyForm);
    setDraft(null);
    setSaved(null);
    setPrepared(null);
    setAnalysisId(null);
    setRetainImage(false);
    setError(null);
    setCaptureKey(Crypto.randomUUID());
    setPhase("intro");
  }

  if (phase === "camera") {
    return (
      <Screen scroll={false}>
        <AppHeader eyebrow="Foto para IA" title="Encuadra la tabla" />
        <View style={styles.cameraFrame}>
          <CameraView
            autofocus="on"
            enableTorch={torchEnabled}
            facing="back"
            mode="picture"
            onCameraReady={() => setCameraReady(true)}
            onMountError={() => { setPhase("intro"); setError("No pudimos iniciar la cámara. Puedes elegir una foto de tu galería."); }}
            ref={cameraRef}
            style={StyleSheet.absoluteFill}
          />
          <View pointerEvents="none" style={styles.guide} />
          <View pointerEvents="none" style={styles.cameraCopy}>
            <Text style={styles.cameraCopyText}>Evita reflejos y llena el marco con la tabla completa.</Text>
          </View>
        </View>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <Button disabled={!cameraReady || processing} label="Capturar y digitalizar" loading={processing} onPress={() => void capture()} />
        <Button disabled={!cameraReady || processing} label={torchEnabled ? "Apagar luz" : "Encender luz"} onPress={() => setTorchEnabled((current) => !current)} variant="secondary" />
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
            <SectionTitle detail={config ? `${config.credits_per_scan} créditos` : "Créditos"} title="Foto, IA y revisión" />
            <Text style={textStyles.muted}>Al continuar, autorizas enviar temporalmente una copia reducida y sin metadatos de la etiqueta a nuestro proveedor de IA. La foto original no se guarda.</Text>
            <View style={styles.steps}>
              <Text style={textStyles.caption}>1 · Usa la cámara o elige una foto clara.</Text>
              <Text style={textStyles.caption}>2 · La IA extrae y valida los valores por 100 g.</Text>
              <Text style={textStyles.caption}>3 · Tú revisas todo antes de crear el alimento.</Text>
            </View>
            {config ? <Text style={textStyles.caption}>Saldo disponible: {config.available_credits} créditos.</Text> : null}
          </Card>
          <Button disabled={config ? !config.can_scan : false} label="Abrir cámara" loading={openingCamera} onPress={() => void beginCamera()} />
          <Button disabled={config ? !config.can_scan : false} label="Elegir desde galería" loading={processing} onPress={() => void chooseFromGallery()} variant="secondary" />
          <Button label="Ingresar manualmente" onPress={() => beginManualReview()} variant="secondary" />
        </>
      ) : null}

      {phase === "review" ? (
        <>
          <InlineNotice tone="warning">La IA puede equivocarse. Compara cada valor con el envase antes de guardar.</InlineNotice>
          {draft?.normalizationStatus === "basis_confirmation_required" ? (
            <Card accent={tokens.color.warning}>
              <SectionTitle title="¿A qué cantidad corresponden estos valores?" />
              <Text style={textStyles.muted}>La foto permitió leer los nutrientes, pero no mostró claramente el encabezado de la columna.</Text>
              <Button label="Corresponden a 100 g" onPress={() => confirmBasis("per_100g")} />
              <Button label="Corresponden a una porción" onPress={() => confirmBasis("per_serving")} variant="secondary" />
              <Button label="Corresponden a 100 ml" onPress={() => confirmBasis("per_100ml")} variant="secondary" />
            </Card>
          ) : null}
          {draft?.normalizationStatus === "serving_size_required" ? (
            <Card accent={tokens.color.warning}>
              <SectionTitle title="Completa el peso de la porción" />
              <Field keyboardType="decimal-pad" label="Peso de la porción (g)" onChangeText={(value) => update("servingSize", value)} value={form.servingSize} />
              <Button label="Convertir a valores por 100 g" onPress={normalizeServingValues} />
            </Card>
          ) : null}
          {draft?.normalizationStatus === "volume_weight_required" ? (
            <Card accent={tokens.color.warning}>
              <SectionTitle title="Convierte 100 ml a 100 g" />
              <Text style={textStyles.muted}>No asumimos que 100 ml pesan 100 g. Busca el peso declarado por volumen o mídelo para evitar alterar los macros.</Text>
              <Field keyboardType="decimal-pad" label="Peso de 100 ml (g)" onChangeText={(value) => update("volumeWeight", value)} value={form.volumeWeight} />
              <Button label="Convertir con este peso" onPress={normalizeVolumeValues} />
            </Card>
          ) : null}
          {draft?.warnings.length ? (
            <Card muted>
              <SectionTitle detail={`${draft.warnings.length}`} title="Puntos por revisar" />
              {draft.warnings.map((warning) => <Text key={warning} style={textStyles.caption}>• {displayWarning(warning)}</Text>)}
            </Card>
          ) : <InlineNotice>La lectura pasó las comprobaciones automáticas. Aun así, confírmala visualmente.</InlineNotice>}
          <Card accent={tokens.color.food}>
            <View style={styles.reviewHeader}>
              <Text style={styles.reviewTitle}>{draft?.normalizationStatus === "ready" ? "Valores por 100 g" : "Valores extraídos"}</Text>
              <Pill color={tokens.color.food} label={analysisId ? "IA" : "Manual"} />
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
            {prepared && analysisId ? (
              <View style={styles.retentionRow}>
                <View style={styles.retentionCopy}>
                  <Text style={textStyles.body}>Guardar copia procesada</Text>
                  <Text style={textStyles.caption}>Opcional. Quedará privada y podrás eliminarla después.</Text>
                </View>
                <Switch onValueChange={setRetainImage} value={retainImage} />
              </View>
            ) : null}
            <Button label="Confirmar y crear alimento" loading={saving} onPress={() => void save()} />
          </Card>
          <Button disabled={saving} label="Usar otra foto" onPress={restart} variant="secondary" />
        </>
      ) : null}

      {phase === "saved" && saved ? (
        <>
          <Card accent={tokens.color.success}>
            <SectionTitle detail={`${Math.round(saved.total_kcal)} kcal`} title={saved.name} />
            <Text style={textStyles.muted}>Creado en tu biblioteca privada · P {saved.protein_g} g · C {saved.carbs_g} g · G {saved.fat_g} g</Text>
            <Text style={textStyles.caption}>{saved.label_image_retained ? "Guardamos sólo la copia procesada que autorizaste." : "La foto utilizada para la lectura no fue guardada."}</Text>
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
  retentionRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  retentionCopy: { flex: 1, gap: tokens.spacing.xs },
});
