import * as Crypto from "expo-crypto";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import { Redirect, useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Image, Modal, Platform, StyleSheet, Switch, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, Field, InlineNotice, Pill, Screen, SectionTitle, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import {
  LABEL_CAMERA_AUTOFOCUS,
  LABEL_CAMERA_FOCUS_SETTLE_MS,
  LABEL_CAMERA_MAX_ZOOM,
  LABEL_CAMERA_ZOOM_STEP,
} from "@/label-capture/camera";
import { deleteCachedImage, prepareLabelImage, type PreparedLabelImage } from "@/label-capture/image";
import {
  classifyLabelImageQuality,
  labelImageQualityMessage,
  type LabelImageQuality,
  unavailableLabelImageQuality,
} from "@/label-capture/quality";
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

type Phase = "intro" | "camera" | "preview" | "review" | "saved";
type LocalCandidate = { basis: string; values: Record<string, number> };
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
  const cameraReadyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const captureInFlightRef = useRef(false);
  const analysisInFlightRef = useRef(false);
  const { status, apiRequest } = useSession();
  const [permission, requestPermission] = useCameraPermissions();
  const [phase, setPhase] = useState<Phase>("intro");
  const [cameraReady, setCameraReady] = useState(false);
  const [openingCamera, setOpeningCamera] = useState(false);
  const [torchEnabled, setTorchEnabled] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [draft, setDraft] = useState<NutritionLabelDraft | null>(null);
  const [saved, setSaved] = useState<FoodLabelCaptureResult | null>(null);
  const [config, setConfig] = useState<FoodLabelAIConfig | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [prepared, setPrepared] = useState<PreparedLabelImage | null>(null);
  const [localCandidate, setLocalCandidate] = useState<LocalCandidate | undefined>();
  const [imageQuality, setImageQuality] = useState<LabelImageQuality>(unavailableLabelImageQuality);
  const [qualityConfidence, setQualityConfidence] = useState<number | null>(null);
  const [retainImage, setRetainImage] = useState(false);
  const [imageExpanded, setImageExpanded] = useState(false);
  const [zoom, setZoom] = useState(0);
  const [availableLenses, setAvailableLenses] = useState<string[]>([]);
  const [selectedLens, setSelectedLens] = useState<string | undefined>();
  const [error, setError] = useState<string | null>(null);
  const [captureKey, setCaptureKey] = useState(Crypto.randomUUID());

  useEffect(() => {
    if (status !== "authenticated") return;
    void apiRequest<FoodLabelAIConfig>("/api/v1/foods/label-captures/config")
      .then(setConfig)
      .catch(() => setConfig(null));
  }, [apiRequest, status]);

  useEffect(() => () => deleteCachedImage(prepared?.uri), [prepared?.uri]);
  useEffect(() => () => {
    if (cameraReadyTimerRef.current) clearTimeout(cameraReadyTimerRef.current);
  }, []);

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
    setLocalCandidate(undefined);
    setImageQuality(unavailableLabelImageQuality);
    setQualityConfidence(null);
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
    setZoom(0);
    setSelectedLens(undefined);
    setAvailableLenses([]);
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

  async function prepareForPreview(uri: string, width: number, height: number) {
    setPreparing(true);
    setError(null);
    let nextPrepared: PreparedLabelImage | null = null;
    try {
      nextPrepared = await prepareLabelImage(uri, width, height);
      let nextLocalCandidate: LocalCandidate | undefined;
      let nextImageQuality = unavailableLabelImageQuality;
      if (Platform.OS === "ios" && isNutritionLabelOcrAvailable()) {
        try {
          const recognition = await recognizeNutritionLabel(nextPrepared.uri);
          const local = normalizeNutritionLabel(recognition);
          nextLocalCandidate = { basis: local.basis, values: local.values as Record<string, number> };
          nextImageQuality = classifyLabelImageQuality(recognition.imageQuality);
        } catch {
          // Devices without a usable local quality signal still get an explicit preview.
        }
      }
      setCaptureKey(Crypto.randomUUID());
      setPrepared(nextPrepared);
      setLocalCandidate(nextLocalCandidate);
      setImageQuality(nextImageQuality);
      setQualityConfidence(null);
      setRetainImage(false);
      setAnalysisId(null);
      setPhase("preview");
    } catch (nextError) {
      deleteCachedImage(nextPrepared?.uri);
      setError(`No pudimos preparar esta foto. ${userFacingError(nextError)}`);
      setPhase("intro");
    } finally {
      deleteCachedImage(uri);
      setPreparing(false);
    }
  }

  async function analyzePreparedImage() {
    if (!prepared || analysisInFlightRef.current || imageQuality.status === "unsuitable") return;
    analysisInFlightRef.current = true;
    setProcessing(true);
    setError(null);
    try {
      const result = await apiRequest<FoodLabelAIAnalysis>("/api/v1/foods/label-captures/analyze", {
        method: "POST",
        body: JSON.stringify({
          image_base64: prepared.base64,
          image_content_type: prepared.contentType,
          image_width: prepared.width,
          image_height: prepared.height,
          idempotency_key: captureKey,
          consent_to_ai_processing: true,
          local_candidate: localCandidate,
        }),
      });
      setAnalysisId(result.analysis_id);
      setQualityConfidence(result.quality_confidence);
      setConfig((current) => current ? { ...current, available_credits: result.available_credits } : current);
      applyDraft(aiDraft(result), result.name);
    } catch (nextError) {
      setError(`${userFacingError(nextError)} Puedes usar otra foto o completar los valores manualmente sin consumir una digitalización fallida.`);
      setPhase("preview");
    } finally {
      analysisInFlightRef.current = false;
      setProcessing(false);
    }
  }

  async function capture() {
    if (!cameraRef.current || !cameraReady || captureInFlightRef.current || preparing || processing) return;
    captureInFlightRef.current = true;
    setCapturing(true);
    setError(null);
    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 1, skipProcessing: false });
      await prepareForPreview(photo.uri, photo.width, photo.height);
    } catch (nextError) {
      setError(`No pudimos capturar esta foto. ${userFacingError(nextError)}`);
    } finally {
      captureInFlightRef.current = false;
      setCapturing(false);
    }
  }

  async function chooseFromGallery() {
    if (preparing || processing) return;
    setPreparing(true);
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
        await prepareForPreview(asset.uri, asset.width, asset.height);
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setPreparing(false);
    }
  }

  function cameraDidBecomeReady() {
    if (cameraReadyTimerRef.current) clearTimeout(cameraReadyTimerRef.current);
    cameraReadyTimerRef.current = setTimeout(() => setCameraReady(true), LABEL_CAMERA_FOCUS_SETTLE_MS);
  }

  function cycleLens() {
    if (availableLenses.length < 2) return;
    const currentIndex = selectedLens ? availableLenses.indexOf(selectedLens) : -1;
    setSelectedLens(availableLenses[(currentIndex + 1) % availableLenses.length]);
    setCameraReady(false);
    cameraDidBecomeReady();
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
    setLocalCandidate(undefined);
    setImageQuality(unavailableLabelImageQuality);
    setQualityConfidence(null);
    setAnalysisId(null);
    setRetainImage(false);
    setError(null);
    setCaptureKey(Crypto.randomUUID());
    setImageExpanded(false);
    setPhase("intro");
  }

  if (phase === "camera") {
    return (
      <Screen scroll={false}>
        <AppHeader eyebrow="Foto para IA" title="Encuadra la tabla" />
        <View style={styles.cameraFrame}>
          <CameraView
            autofocus={LABEL_CAMERA_AUTOFOCUS}
            enableTorch={torchEnabled}
            facing="back"
            mode="picture"
            onAvailableLensesChanged={({ lenses }) => setAvailableLenses(lenses)}
            onCameraReady={cameraDidBecomeReady}
            onMountError={() => { setPhase("intro"); setError("No pudimos iniciar la cámara. Puedes elegir una foto de tu galería."); }}
            ref={cameraRef}
            selectedLens={selectedLens}
            style={StyleSheet.absoluteFill}
            zoom={zoom}
          />
          <View pointerEvents="none" style={styles.guide} />
          <View pointerEvents="none" style={styles.cameraCopy}>
            <Text style={styles.cameraCopyText}>Mantén el teléfono paralelo y aléjalo hasta ver el texto nítido. Usa zoom en vez de acercarte demasiado.</Text>
          </View>
        </View>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        {!cameraReady ? <Text style={textStyles.caption}>Preparando enfoque continuo…</Text> : null}
        <Button disabled={!cameraReady || capturing || preparing} label="Capturar foto" loading={capturing || preparing} onPress={() => void capture()} />
        <View style={styles.cameraControls}>
          <Button disabled={!cameraReady || capturing || zoom <= 0} label="Alejar" onPress={() => setZoom((current) => Math.max(0, current - LABEL_CAMERA_ZOOM_STEP))} variant="secondary" />
          <Button disabled={!cameraReady || capturing || zoom >= LABEL_CAMERA_MAX_ZOOM} label="Acercar" onPress={() => setZoom((current) => Math.min(LABEL_CAMERA_MAX_ZOOM, current + LABEL_CAMERA_ZOOM_STEP))} variant="secondary" />
        </View>
        {availableLenses.length > 1 ? <Button disabled={capturing || preparing} label="Cambiar lente" onPress={cycleLens} variant="secondary" /> : null}
        <Button disabled={!cameraReady || capturing || preparing} label={torchEnabled ? "Apagar luz" : "Encender luz"} onPress={() => setTorchEnabled((current) => !current)} variant="secondary" />
        <Button disabled={capturing || preparing} label="Cancelar" onPress={restart} variant="secondary" />
      </Screen>
    );
  }

  if (phase === "preview" && prepared) {
    return (
      <Screen>
        <AppHeader eyebrow="Antes de usar créditos" title="Revisa la fotografía" />
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <Image accessibilityLabel="Fotografía procesada de la etiqueta nutricional" resizeMode="contain" source={{ uri: prepared.uri }} style={styles.previewImage} />
        {imageQuality.status === "suitable" ? <InlineNotice>La imagen superó las comprobaciones locales de legibilidad.</InlineNotice> : null}
        {imageQuality.status === "reviewable" ? <InlineNotice tone="warning">La imagen puede usarse, pero conviene revisar estos puntos antes de continuar.</InlineNotice> : null}
        {imageQuality.status === "unsuitable" ? <InlineNotice tone="error">Esta imagen no es suficientemente legible y no será enviada ni consumirá créditos.</InlineNotice> : null}
        {imageQuality.status === "unavailable" ? <InlineNotice tone="warning">No pudimos comprobar automáticamente la nitidez. Confirma visualmente que todo el texto sea legible.</InlineNotice> : null}
        {imageQuality.issues.map((issue) => <Text key={issue} style={textStyles.caption}>• {labelImageQualityMessage(issue)}</Text>)}
        <Button disabled={imageQuality.status === "unsuitable" || processing} label="Usar esta foto" loading={processing} onPress={() => void analyzePreparedImage()} />
        <Button disabled={processing} label="Usar otra foto" onPress={restart} variant="secondary" />
        <Button disabled={processing} label="Ingresar manualmente" onPress={() => beginManualReview()} variant="secondary" />
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
          <Button disabled={config ? !config.can_scan : false} label="Elegir desde galería" loading={preparing} onPress={() => void chooseFromGallery()} variant="secondary" />
          <Button label="Ingresar manualmente" onPress={() => beginManualReview()} variant="secondary" />
        </>
      ) : null}

      {phase === "review" ? (
        <>
          <InlineNotice tone="warning">La IA puede equivocarse. Compara cada valor con el envase antes de guardar.</InlineNotice>
          {prepared ? (
            <Card>
              <SectionTitle detail="Imagen analizada" title="Compara la lectura" />
              <Image accessibilityLabel="Etiqueta nutricional analizada" resizeMode="contain" source={{ uri: prepared.uri }} style={styles.reviewImage} />
              <Button label="Ampliar foto" onPress={() => setImageExpanded(true)} variant="secondary" />
            </Card>
          ) : null}
          {qualityConfidence !== null ? (
            <InlineNotice tone={qualityConfidence < 0.82 ? "warning" : undefined}>
              {qualityConfidence >= 0.9
                ? "La extracción tiene confianza alta. Confirma igualmente cada valor."
                : qualityConfidence >= 0.82
                  ? "La extracción es utilizable, pero revisa cuidadosamente cada valor."
                  : "La extracción tiene confianza baja. Revisa y corrige cada campo antes de guardar."}
            </InlineNotice>
          ) : null}
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
      <Modal animationType="fade" onRequestClose={() => setImageExpanded(false)} transparent visible={imageExpanded}>
        <View style={styles.imageModal}>
          {prepared ? <Image accessibilityLabel="Vista ampliada de la etiqueta nutricional" resizeMode="contain" source={{ uri: prepared.uri }} style={styles.expandedImage} /> : null}
          <Button label="Cerrar" onPress={() => setImageExpanded(false)} />
        </View>
      </Modal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  cameraFrame: { borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.card, borderWidth: 1, flex: 1, minHeight: 420, overflow: "hidden" },
  guide: { borderColor: tokens.color.food, borderRadius: tokens.radius.lg, borderWidth: 3, bottom: 70, left: 24, position: "absolute", right: 24, top: 52 },
  cameraCopy: { backgroundColor: "rgba(0,0,0,0.72)", bottom: 0, left: 0, padding: 16, position: "absolute", right: 0 },
  cameraCopyText: { color: tokens.color.textMain, fontSize: 13, lineHeight: 18, textAlign: "center" },
  cameraControls: { flexDirection: "row", gap: tokens.spacing.sm },
  previewImage: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.card, height: 420, width: "100%" },
  reviewImage: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, height: 260, width: "100%" },
  imageModal: { backgroundColor: "rgba(0,0,0,0.94)", flex: 1, justifyContent: "center", padding: tokens.spacing.md },
  expandedImage: { flex: 1, width: "100%" },
  steps: { gap: tokens.spacing.sm },
  reviewHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  reviewTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: "800" },
  fieldRow: { flexDirection: "row", gap: tokens.spacing.sm },
  fieldCell: { flex: 1 },
  retentionRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  retentionCopy: { flex: 1, gap: tokens.spacing.xs },
});
