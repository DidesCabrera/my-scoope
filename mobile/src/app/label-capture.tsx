import * as Crypto from "expo-crypto";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { Camera, Check, CheckCheck, ScanLine } from "lucide-react-native";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Image, Platform, StyleSheet, Text, TextInput, View, type StyleProp, type ViewStyle } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from "react-native-reanimated";
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from "react-native-svg";

import { userFacingError } from "@/api/errors";
import { useSession } from "@/auth/session-context";
import { AssistantCreditBalance } from "@/components/assistant/assistant-credit-balance";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { NutritionEntityCard } from "@/components/nutrition";
import { Button, Card, EntityIcon, Field, InlineNotice, MacroLoadingIndicator, Pill, Screen, SectionHeading, SectionTitle, SystemSwitch, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import {
  LABEL_CAMERA_AUTOFOCUS,
  LABEL_CAMERA_FOCUS_SETTLE_MS,
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

type Phase = "intro" | "camera" | "preview" | "processing" | "review" | "confirmation" | "saved";
type CaptureSource = "camera" | "gallery";
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
  basis_per_100ml_requires_weight: "La etiqueta está expresada por 100 ml y se conservará en esa unidad.",
  basis_normalized_from_100ml: "Los valores corresponden a 100 ml.",
  basis_not_detected: "Confirma si los valores corresponden a 100 g, 100 ml o una porción.",
  serving_size_required: "Indica el peso en gramos de la porción impresa.",
  energy_macro_mismatch: "Las calorías declaradas difieren del cálculo de proteínas, carbos y grasas.",
  model_escalation_unresolved: "La lectura requirió comprobaciones adicionales. Revisa con especial atención.",
};

function ZoomableLabelImage({ accessibilityLabel, uri }: { accessibilityLabel: string; uri: string }) {
  const scale = useSharedValue(1);
  const savedScale = useSharedValue(1);
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const savedTranslateX = useSharedValue(0);
  const savedTranslateY = useSharedValue(0);
  const pinch = Gesture.Pinch()
    .onUpdate((event) => { scale.value = Math.min(4, Math.max(1, savedScale.value * event.scale)); })
    .onEnd(() => {
      savedScale.value = scale.value;
      if (scale.value === 1) {
        translateX.value = withTiming(0);
        translateY.value = withTiming(0);
        savedTranslateX.value = 0;
        savedTranslateY.value = 0;
      }
    });
  const pan = Gesture.Pan()
    .averageTouches(true)
    .onUpdate((event) => {
      if (scale.value > 1) {
        translateX.value = savedTranslateX.value + event.translationX;
        translateY.value = savedTranslateY.value + event.translationY;
      }
    })
    .onEnd(() => {
      savedTranslateX.value = translateX.value;
      savedTranslateY.value = translateY.value;
    });
  const doubleTap = Gesture.Tap().numberOfTaps(2).onEnd(() => {
    const nextScale = scale.value > 1 ? 1 : 2;
    scale.value = withTiming(nextScale);
    savedScale.value = nextScale;
    if (nextScale === 1) {
      translateX.value = withTiming(0);
      translateY.value = withTiming(0);
      savedTranslateX.value = 0;
      savedTranslateY.value = 0;
    }
  });
  const gesture = Gesture.Simultaneous(pinch, pan, doubleTap);
  const imageStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { scale: scale.value },
    ],
  }));
  return (
    <GestureDetector gesture={gesture}>
      <Animated.Image accessibilityLabel={accessibilityLabel} resizeMode="contain" source={{ uri }} style={[StyleSheet.absoluteFill, imageStyle]} />
    </GestureDetector>
  );
}

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

function FullBleedSquare({ children, surfaceStyle }: { children: ReactNode; surfaceStyle?: StyleProp<ViewStyle> }) {
  const [contentWidth, setContentWidth] = useState(0);
  const size = contentWidth ? contentWidth + tokens.spacing.screen * 2 : undefined;
  return (
    <View
      onLayout={({ nativeEvent }) => setContentWidth((current) => current === nativeEvent.layout.width ? current : nativeEvent.layout.width)}
      style={[styles.fullBleedSquareLayout, size ? { height: size } : styles.fullBleedSquareFallback]}>
      <View style={[surfaceStyle, styles.fullBleedSquareSurface, size ? { height: size, width: size } : styles.fullBleedSquareSurfaceFallback]}>{children}</View>
    </View>
  );
}

function CreditFocusGuide() {
  const [size, setSize] = useState({ height: 0, width: 0 });
  return (
    <View
      onLayout={({ nativeEvent }) => {
        const next = nativeEvent.layout;
        setSize((current) => current.height === next.height && current.width === next.width ? current : { height: next.height, width: next.width });
      }}
      pointerEvents="none"
      style={styles.guide}>
      {size.width > 4 && size.height > 4 ? (
        <Svg aria-hidden height={size.height} width={size.width}>
          <Defs>
            <LinearGradient id="label-capture-live-guide" x1="0" x2="1" y1="0" y2="1">
              <Stop offset="0" stopColor={tokens.color.protein} />
              <Stop offset="0.5" stopColor={tokens.color.carbs} />
              <Stop offset="1" stopColor={tokens.color.fat} />
            </LinearGradient>
          </Defs>
          <Rect fill="none" height={size.height - 4} rx={tokens.radius.lg} ry={tokens.radius.lg} stroke="url(#label-capture-live-guide)" strokeWidth="4" width={size.width - 4} x="2" y="2" />
        </Svg>
      ) : null}
    </View>
  );
}

function CreditTaskIcon({ complete, id }: { complete: boolean; id: string }) {
  return (
    <Svg aria-hidden height="18" viewBox="0 0 18 18" width="18">
      <Defs>
        <LinearGradient id={id} x1="0" x2="1" y1="0" y2="1">
          <Stop offset="0" stopColor={tokens.color.protein} />
          <Stop offset="0.5" stopColor={tokens.color.carbs} />
          <Stop offset="1" stopColor={tokens.color.fat} />
        </LinearGradient>
      </Defs>
      {complete
        ? <Path d="M3 9.5 7 13.5 15 5.5" fill="none" stroke={`url(#${id})`} strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.2" />
        : <Circle cx="9" cy="9" fill="none" r="7" stroke={`url(#${id})`} strokeWidth="2.2" />}
    </Svg>
  );
}

function nutritionSummary(protein: number, carbs: number, fat: number, declaredEnergy?: number) {
  const proteinCalories = protein * 4;
  const carbsCalories = carbs * 4;
  const fatCalories = fat * 9;
  const macroCalories = proteinCalories + carbsCalories + fatCalories;
  const allocation = (value: number) => macroCalories > 0 ? value / macroCalories * 100 : 0;
  return {
    calories: declaredEnergy ?? macroCalories,
    protein: { grams: protein, allocation: allocation(proteinCalories) },
    carbs: { grams: carbs, allocation: allocation(carbsCalories) },
    fat: { grams: fat, allocation: allocation(fatCalories) },
  };
}

export default function LabelCaptureScreen() {
  const router = useRouter();
  const setHeaderPresentation = useHeaderPresentation();
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
  const [aiConsentGranted, setAiConsentGranted] = useState(false);
  const [captureSource, setCaptureSource] = useState<CaptureSource>("camera");
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

  function beginManualReview(message?: string) {
    deleteCachedImage(prepared?.uri);
    setPrepared(null);
    setLocalCandidate(undefined);
    setImageQuality(unavailableLabelImageQuality);
    setQualityConfidence(null);
    setAnalysisId(null);
    setRetainImage(false);
    setAiConsentGranted(false);
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
    setCaptureSource("camera");
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
      setAiConsentGranted(false);
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
    if (!prepared || !aiConsentGranted || analysisInFlightRef.current || imageQuality.status === "unsuitable") return;
    analysisInFlightRef.current = true;
    setProcessing(true);
    setError(null);
    setPhase("processing");
    try {
      const result = await apiRequest<FoodLabelAIAnalysis>("/api/v1/foods/label-captures/analyze", {
        method: "POST",
        body: JSON.stringify({
          image_base64: prepared.base64,
          image_content_type: prepared.contentType,
          image_width: prepared.width,
          image_height: prepared.height,
          idempotency_key: captureKey,
          consent_to_ai_processing: aiConsentGranted,
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
    setCaptureSource("gallery");
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

  async function retakePhoto() {
    deleteCachedImage(prepared?.uri);
    setPrepared(null);
    setLocalCandidate(undefined);
    setImageQuality(unavailableLabelImageQuality);
    await beginCamera();
  }

  function continueToConfirmation() {
    if (draft?.normalizationStatus !== "ready") {
      setError("Confirma la base y completa la conversión antes de continuar.");
      return;
    }
    const requiredValues = [optionalNumber(form.protein), optionalNumber(form.carbs), optionalNumber(form.fat)];
    if (!form.name.trim() || requiredValues.some((value) => value === undefined)) {
      setError("Completa el nombre, proteínas, carbos y grasas antes de continuar.");
      return;
    }
    const optionalInputs = [form.energy, form.saturatedFat, form.sugar, form.fiber, form.sodium, form.servingSize, form.volumeWeight];
    if (optionalInputs.some((value) => value.trim() && optionalNumber(value) === undefined)) {
      setError("Revisa los campos opcionales: usa sólo números positivos o déjalos vacíos.");
      return;
    }
    setError(null);
    setPhase("confirmation");
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
      volume_weight_g_per_100ml: undefined,
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

  const restart = useCallback(() => {
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
    setAiConsentGranted(false);
    setError(null);
    setCaptureKey(Crypto.randomUUID());
    setCaptureSource("camera");
    setPhase("intro");
  }, [prepared?.uri]);

  useFocusEffect(useCallback(() => {
    const hiddenLeadingAction = { icon: "none" as const, label: "", onPress: () => undefined };
    if (phase === "intro") {
      setHeaderPresentation({ fallback: "/today", mode: "back", title: "Digitalizar etiqueta" });
    } else if (phase === "camera") {
      setHeaderPresentation({ action: { label: "Cancelar", onPress: restart }, leadingAction: { icon: "back", label: "Volver", onPress: restart }, mode: "back", title: "Tomar foto" });
    } else if (phase === "preview") {
      const back = () => setPhase(captureSource === "camera" ? "camera" : "intro");
      setHeaderPresentation({ action: { label: "Cancelar", onPress: restart }, leadingAction: { icon: "back", label: "Volver", onPress: back }, mode: "back", title: "Confirmación calidad" });
    } else if (phase === "processing") {
      setHeaderPresentation({ leadingAction: hiddenLeadingAction, mode: "back", title: "Analizando información" });
    } else if (phase === "review") {
      setHeaderPresentation({ action: { label: "Cancelar", onPress: restart }, leadingAction: hiddenLeadingAction, mode: "back", title: "Revisión de información" });
    } else if (phase === "confirmation") {
      setHeaderPresentation({ action: { label: "Cancelar", onPress: restart }, leadingAction: { icon: "back", label: "Volver", onPress: () => setPhase("review") }, mode: "back", title: "Crear Alimento" });
    } else {
      setHeaderPresentation({ action: { label: "Listo", onPress: () => router.back() }, leadingAction: hiddenLeadingAction, mode: "back", title: "" });
    }
    return () => setHeaderPresentation({ mode: "default" });
  }, [captureSource, phase, restart, router, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;

  if (phase === "camera") {
    return (
      <Screen contentStyle={styles.fixedScreen} headerMode="preserve" scroll={false}>
        <FullBleedSquare surfaceStyle={styles.cameraFrame}>
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
            zoom={0}
          />
          <CreditFocusGuide />
          <View pointerEvents="none" style={styles.focusBadge}>
            <ScanLine color={tokens.color.textMain} size={15} />
            <Text style={styles.focusText}>{cameraReady ? "Enfoque listo" : "Preparando enfoque"}</Text>
          </View>
        </FullBleedSquare>
        <View style={styles.photoMessage}><Text style={styles.photoMessageText}>Intenta tomar la foto con buena iluminación y sin movimiento. Una mejor calidad de la foto facilitará un mejor resultado.</Text></View>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <View style={styles.bottomActions}>
          <Button disabled={!cameraReady || capturing || preparing} label="Capturar foto" loading={capturing || preparing} onPress={() => void capture()} />
          {availableLenses.length > 1 ? <Button disabled={capturing || preparing} label="Cambiar lente" onPress={cycleLens} variant="secondary" /> : null}
          <Button disabled={!cameraReady || capturing || preparing} label={torchEnabled ? "Apagar luz" : "Encender luz"} onPress={() => setTorchEnabled((current) => !current)} variant="secondary" />
        </View>
      </Screen>
    );
  }

  if (phase === "preview" && prepared) {
    const qualityPresentation = imageQuality.status === "suitable"
      ? { detail: "La fotografía superó las comprobaciones de nitidez, encuadre y perspectiva. Confirma que el encabezado y todas las filas estén visibles.", label: "Óptima", title: "Lista para digitalizar", tone: tokens.color.success }
      : imageQuality.status === "reviewable"
        ? { detail: "La imagen puede usarse, pero revisa los puntos detectados antes de continuar.", label: "Revisar", title: "Comprueba la fotografía", tone: tokens.color.warning }
        : imageQuality.status === "unsuitable"
          ? { detail: "La imagen no es suficientemente legible y no será enviada ni consumirá créditos.", label: "No apta", title: "Toma otra fotografía", tone: tokens.color.danger }
          : { detail: "No pudimos comprobar automáticamente la nitidez. Confirma visualmente que todo el texto sea legible.", label: "Sin validar", title: "Comprueba la fotografía", tone: tokens.color.warning };
    return (
      <Screen headerMode="preserve">
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <FullBleedSquare><Image accessibilityLabel="Fotografía procesada de la etiqueta nutricional" resizeMode="contain" source={{ uri: prepared.uri }} style={StyleSheet.absoluteFill} /></FullBleedSquare>
        <View style={styles.qualityPanel}>
          <View style={styles.qualityCopy}>
            <Text style={styles.qualityTitle}>{qualityPresentation.title}</Text>
            <Text style={styles.qualityDetail}>{qualityPresentation.detail}</Text>
            {imageQuality.issues.map((issue) => <Text key={issue} style={styles.qualityIssue}>• {labelImageQualityMessage(issue)}</Text>)}
          </View>
          <Pill color={qualityPresentation.tone} label={qualityPresentation.label} />
        </View>
        <View style={styles.bottomActions}>
          <View style={styles.retentionPanel}>
            <View style={styles.retentionRow}>
              <View style={styles.retentionCopy}>
                <Text style={styles.retentionTitle}>Autorizar análisis con OpenAI</Text>
                <Text style={styles.retentionDetail}>Se enviará temporalmente esta copia reducida y sin metadatos para extraer los valores. No se usa para publicidad ni se conserva en OpenAI.</Text>
              </View>
              <SystemSwitch accessibilityLabel="Autorizar análisis con OpenAI" onValueChange={setAiConsentGranted} value={aiConsentGranted} />
            </View>
          </View>
          <Button disabled={!aiConsentGranted || imageQuality.status === "unsuitable" || processing} label={`Enviar a OpenAI y digitalizar${config ? ` · ${config.credits_per_scan} ${config.credits_per_scan === 1 ? "crédito" : "créditos"}` : ""}`} loading={processing} onPress={() => void analyzePreparedImage()} />
          <Button disabled={processing} label="Tomar otra foto" onPress={() => void retakePhoto()} variant="secondary" />
        </View>
      </Screen>
    );
  }

  if (phase === "processing" && prepared) {
    return (
      <Screen headerMode="preserve">
        <FullBleedSquare surfaceStyle={styles.processingPhoto}>
          <Image accessibilityLabel="Etiqueta nutricional en análisis" resizeMode="contain" source={{ uri: prepared.uri }} style={StyleSheet.absoluteFill} />
          <View style={styles.scanBeam}>
            <Svg aria-hidden height="100%" width="100%">
              <Defs>
                <LinearGradient id="label-capture-live-scan" x1="0" x2="1" y1="0" y2="0">
                  <Stop offset="0" stopColor={tokens.color.protein} />
                  <Stop offset="0.5" stopColor={tokens.color.carbs} />
                  <Stop offset="1" stopColor={tokens.color.fat} />
                </LinearGradient>
              </Defs>
              <Rect fill="url(#label-capture-live-scan)" height="100%" rx="2" ry="2" width="100%" />
            </Svg>
          </View>
        </FullBleedSquare>
        <View style={styles.processingDetails}>
          <View style={styles.processingHeader}>
            <View style={styles.qualityCopy}><Text style={styles.processingTitle}>Analizando valores</Text><Text style={styles.qualityDetail}>Identificando la base nutricional de la etiqueta.</Text></View>
            <MacroLoadingIndicator accessibilityLabel="Analizando los valores nutricionales" style={styles.processingLoading} />
          </View>
          <View style={styles.taskList}>
            <View style={styles.taskRow}><CreditTaskIcon complete id="live-credit-task-text" /><Text style={styles.taskDone}>Texto reconocido</Text></View>
            <View style={styles.taskRow}><CreditTaskIcon complete id="live-credit-task-column" /><Text style={styles.taskDone}>Columna nutricional identificada</Text></View>
            <View style={styles.taskRow}><CreditTaskIcon complete={false} id="live-credit-task-nutrients" /><Text style={styles.taskActive}>Comprobando nutrientes…</Text></View>
          </View>
        </View>
        <Text style={styles.quietCenter}>No cierres esta pantalla. Suele tardar pocos segundos.</Text>
      </Screen>
    );
  }

  const formNutrition = nutritionSummary(
    optionalNumber(form.protein) ?? 0,
    optionalNumber(form.carbs) ?? 0,
    optionalNumber(form.fat) ?? 0,
    optionalNumber(form.energy),
  );

  const nutrientRows: { field: keyof FormState; label: string; unit: string }[] = [
    { field: "energy", label: "Energía", unit: "kcal" },
    { field: "protein", label: "Proteínas", unit: "g" },
    { field: "carbs", label: "Carbohidratos", unit: "g" },
    { field: "fat", label: "Grasas totales", unit: "g" },
    { field: "saturatedFat", label: "Grasas saturadas", unit: "g" },
    { field: "sugar", label: "Azúcares", unit: "g" },
    { field: "fiber", label: "Fibra", unit: "g" },
    { field: "sodium", label: "Sodio", unit: "mg" },
  ];
  const portionUnit = draft?.basis === "per_100ml" ? "ml" : "g";

  return (
    <Screen
      contentStyle={phase === "review" && prepared ? styles.reviewScrollContent : undefined}
      headerMode="preserve"
      stickyHeader={phase === "review" && prepared ? (
        <FullBleedSquare surfaceStyle={styles.reviewPhoto}>
          <ZoomableLabelImage accessibilityLabel="Etiqueta nutricional analizada" uri={prepared.uri} />
        </FullBleedSquare>
      ) : undefined}
      stickyHeaderStyle={styles.reviewStickyHeader}
    >
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}

      {phase === "intro" ? (
        <>
          <View style={styles.introHeader}>
            <Camera color={tokens.color.textMain} size={34} strokeWidth={1.8} />
            <Text style={styles.eyebrow}>DIGITALIZAR ETIQUETA</Text>
            <Text style={styles.introTitle}>Convierte una etiqueta en segundos</Text>
            <Text style={styles.introDescription}>Fotografía la tabla nutricional y crea un alimento privado sin transcribir cada dato.</Text>
          </View>
          <View style={styles.assuranceList}>
            <View style={styles.assuranceRow}><Camera color={tokens.color.textMuted} size={17} /><Text style={styles.assuranceText}>Captura o elige una foto clara.</Text></View>
            <View style={styles.assuranceRow}><CheckCheck color={tokens.color.textMuted} size={17} /><Text style={styles.assuranceText}>Validamos nitidez antes de usar créditos.</Text></View>
            <View style={styles.assuranceRow}><Check color={tokens.color.textMuted} size={17} /><Text style={styles.assuranceText}>Tú confirmas cada valor antes de guardar.</Text></View>
          </View>
          <InlineNotice>Enviaremos una copia reducida y sin metadatos para extraer los valores. La fotografía original no se guarda.</InlineNotice>
          <View style={styles.introBottom}>
            {config ? <AssistantCreditBalance availability={{ available_credits: config.available_credits }} contained /> : null}
            <View style={styles.actionGroup}>
              <Button disabled={config ? !config.can_scan : false} label="Abrir cámara" loading={openingCamera} onPress={() => void beginCamera()} />
              <Button disabled={config ? !config.can_scan : false} label="Elegir desde galería" loading={preparing} onPress={() => void chooseFromGallery()} variant="secondary" />
              <Button label="Ingresar manualmente" onPress={() => beginManualReview()} variant="secondary" />
            </View>
          </View>
        </>
      ) : null}

      {phase === "review" ? (
        <>
          {prepared ? (
            <View style={[styles.photoMessage, styles.reviewPhotoMessage]}>
              <Text style={styles.photoMessageText}>
                {qualityConfidence === null
                  ? "La lectura pasó las comprobaciones automáticas. Confirma cada valor con la etiqueta."
                  : qualityConfidence >= 0.9
                    ? "Confianza alta. La lectura pasó las comprobaciones automáticas."
                    : qualityConfidence >= 0.82
                      ? "Lectura utilizable. Revisa cuidadosamente cada valor."
                      : "Confianza baja. Corrige cada campo comparándolo con la etiqueta."}
              </Text>
            </View>
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
          {draft?.warnings.length ? (
            <View style={styles.warningList}>
              <Text style={styles.warningTitle}>Puntos por revisar</Text>
              {draft.warnings.map((warning) => <Text key={warning} style={textStyles.caption}>• {displayWarning(warning)}</Text>)}
            </View>
          ) : null}
          <View style={styles.reviewForm}>
            <Text style={styles.reviewTitle}>{draft?.normalizationStatus === "ready" ? `Valores por 100 ${draft.basis === "per_100ml" ? "ml" : "g"}` : "Valores extraídos"}</Text>
            <View style={styles.nutritionRows}>
              {nutrientRows.map((item) => (
                <View key={item.field} style={styles.nutritionRow}>
                  <Text style={styles.nutritionLabel}>{item.label}</Text>
                  <View style={styles.nutritionInputSurface}>
                    <TextInput accessibilityLabel={item.label} keyboardType="decimal-pad" onChangeText={(value) => update(item.field, value)} selectTextOnFocus style={styles.nutritionInput} value={form[item.field]} />
                    <Text style={styles.nutritionUnit}>{item.unit}</Text>
                  </View>
                </View>
              ))}
              <View style={[styles.nutritionRow, styles.portionRow]}>
                <Text style={[styles.nutritionLabel, styles.nutritionLabelEmphasis]}>Tamaño de la porción</Text>
                <View style={styles.nutritionInputSurface}>
                  <TextInput accessibilityLabel="Tamaño de la porción" keyboardType="decimal-pad" onChangeText={(value) => update("servingSize", value)} selectTextOnFocus style={styles.nutritionInput} value={form.servingSize} />
                  <Text style={styles.nutritionUnit}>{portionUnit}</Text>
                </View>
              </View>
            </View>
            <Field autoCapitalize="words" label="Nombre del producto" labelIcon={<EntityIcon entity="food" size="compact" />} onChangeText={(value) => update("name", value)} placeholder="Ej. Yogur griego natural" value={form.name} />
          </View>
          <View style={styles.reviewContinue}><Button label="Continuar" onPress={continueToConfirmation} /></View>
        </>
      ) : null}

      {phase === "confirmation" ? (
        <>
          <View style={styles.confirmationHeading}>
            <SectionHeading icon={<CheckCheck color={tokens.color.entityIconForeground} size={18} />} title="Confirma el alimento" />
            <Text style={styles.confirmationSubtitle}>Al guardar confirmas que comparaste los valores con la etiqueta.</Text>
          </View>
          <NutritionEntityCard entity="food" indicators={[{ label: "base nutricional", value: `100 ${portionUnit}` }]} nutrition={formNutrition} title={form.name.trim() || "Alimento sin nombre"} />
          {prepared && analysisId ? (
            <View style={styles.retentionPanel}>
              <View style={styles.retentionRow}>
                <View style={styles.retentionCopy}>
                  <Text style={styles.retentionTitle}>Guardar copia procesada</Text>
                  <Text style={styles.retentionDetail}>Opcional, privada y eliminable después.</Text>
                </View>
                <SystemSwitch accessibilityLabel="Guardar copia procesada" onValueChange={setRetainImage} value={retainImage} />
              </View>
            </View>
          ) : null}
          <View style={styles.bottomActions}>
            <Button label="Confirmar y crear alimento" loading={saving} onPress={() => void save()} />
            <Button disabled={saving} label="Volver a revisar" onPress={() => setPhase("review")} variant="secondary" />
          </View>
        </>
      ) : null}

      {phase === "saved" && saved ? (
        <>
          <View style={styles.successHero}>
            <View style={styles.successIcon}>
              <Svg aria-hidden height="100%" pointerEvents="none" style={StyleSheet.absoluteFill} viewBox="0 0 64 64" width="100%">
                <Defs>
                  <LinearGradient id="label-capture-live-success" x1="0" x2="1" y1="0" y2="1">
                    <Stop offset="0" stopColor={tokens.color.protein} />
                    <Stop offset="0.5" stopColor={tokens.color.carbs} />
                    <Stop offset="1" stopColor={tokens.color.fat} />
                  </LinearGradient>
                </Defs>
                <Circle cx="32" cy="32" fill="url(#label-capture-live-success)" r="32" />
              </Svg>
              <Check color={tokens.color.surfaceApp} size={32} />
            </View>
            <Text style={styles.successTitle}>{saved.name}</Text>
            <Text style={styles.successDetail}>Creado en tu biblioteca privada</Text>
          </View>
          <NutritionEntityCard
            entity="food"
            indicators={[{ label: "base nutricional", value: `100 ${saved.portion_unit}` }]}
            nutrition={nutritionSummary(saved.protein_g, saved.carbs_g, saved.fat_g, saved.total_kcal)}
            title={saved.name}
          />
          <InlineNotice>{saved.label_image_retained ? "Guardamos sólo la copia procesada que autorizaste." : "La fotografía utilizada para la lectura no fue guardada."}</InlineNotice>
          <View style={styles.bottomActions}>
            <Button label="Ver alimento" onPress={() => router.push(`/libraries/foods/${saved.id}` as Href)} />
            <Button label="Digitalizar otra etiqueta" onPress={restart} variant="secondary" />
          </View>
        </>
      ) : null}

    </Screen>
  );
}

const styles = StyleSheet.create({
  fixedScreen: { flexGrow: 1, paddingBottom: tokens.spacing.lg },
  fullBleedSquareLayout: { marginTop: -tokens.spacing.lg, position: "relative" },
  fullBleedSquareFallback: { aspectRatio: 1 },
  fullBleedSquareSurface: { left: -tokens.spacing.screen, overflow: "hidden", position: "absolute", top: 0 },
  fullBleedSquareSurfaceFallback: { bottom: 0, right: -tokens.spacing.screen },
  cameraFrame: { backgroundColor: "#0C1118", borderBottomColor: tokens.color.borderDefault, borderBottomWidth: 1, borderTopColor: tokens.color.borderDefault, borderTopWidth: 1, justifyContent: "center" },
  guide: { aspectRatio: 1, borderRadius: tokens.radius.lg, left: 22, overflow: "hidden", position: "absolute", right: 22, top: 22 },
  focusBadge: { alignItems: "center", alignSelf: "center", backgroundColor: "rgba(5,10,15,0.86)", borderRadius: tokens.radius.pill, flexDirection: "row", gap: 6, paddingHorizontal: 12, paddingVertical: 7, position: "absolute", top: 46 },
  focusText: { color: tokens.color.textMain, fontSize: 11, fontWeight: tokens.weight.bold },
  photoMessage: { backgroundColor: tokens.color.surfaceCard, marginHorizontal: -tokens.spacing.screen, marginTop: -tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  photoMessageText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  bottomActions: { gap: tokens.spacing.sm, marginTop: "auto" },
  qualityPanel: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, flexDirection: "row", gap: tokens.spacing.sm, marginHorizontal: -tokens.spacing.screen, marginTop: -tokens.spacing.lg, padding: tokens.card.outerPadding },
  qualityCopy: { flex: 1, gap: 2 },
  qualityTitle: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  qualityDetail: { color: tokens.color.textMuted, fontSize: 11, lineHeight: 16 },
  qualityIssue: { color: tokens.color.textSoft, fontSize: 11, lineHeight: 16 },
  processingPhoto: { position: "relative" },
  scanBeam: { borderRadius: tokens.radius.pill, height: 3, left: tokens.spacing.lg, overflow: "hidden", position: "absolute", right: tokens.spacing.lg, top: "50%", transform: [{ translateY: -1.5 }] },
  processingDetails: { gap: tokens.spacing.sm },
  processingHeader: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  processingLoading: { flexShrink: 0, marginLeft: -16, marginRight: 2, transform: [{ translateX: 16 }, { scale: 0.6 }] },
  processingTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.bold, lineHeight: 25 },
  taskList: { gap: tokens.spacing.sm, marginTop: tokens.spacing.sm, paddingTop: tokens.spacing.md },
  taskRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  taskDone: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  taskActive: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  quietCenter: { color: tokens.color.textSoft, fontSize: 11, lineHeight: 16, marginTop: 20, textAlign: "center" },
  introHeader: { alignItems: "flex-start", gap: tokens.spacing.sm },
  eyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, letterSpacing: 1.2, marginTop: tokens.spacing.md },
  introTitle: { color: tokens.color.textMain, fontSize: 27, fontWeight: tokens.weight.extraBold, letterSpacing: -0.7, lineHeight: 32 },
  introDescription: { color: tokens.color.textMain, fontSize: tokens.type.body, lineHeight: 22, marginTop: tokens.spacing.sm },
  assuranceList: { gap: tokens.spacing.sm, marginTop: tokens.spacing.xs },
  assuranceRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  assuranceText: { color: tokens.color.textMuted, flex: 1, fontSize: tokens.type.caption, lineHeight: 19 },
  introBottom: { gap: tokens.spacing.sm, marginTop: "auto" },
  actionGroup: { gap: tokens.spacing.sm },
  reviewStickyHeader: { paddingBottom: 0, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  reviewScrollContent: { paddingTop: 0 },
  reviewPhotoMessage: { marginTop: 0 },
  reviewPhoto: { backgroundColor: "#18202A", position: "relative" },
  warningList: { gap: tokens.spacing.xs },
  warningTitle: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  reviewForm: { gap: tokens.card.gap, marginTop: tokens.spacing.sm },
  reviewContinue: { marginTop: tokens.spacing.xl },
  reviewTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.extraBold },
  nutritionRows: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, marginTop: -tokens.spacing.xs },
  nutritionRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 46, paddingLeft: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  portionRow: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, marginTop: tokens.spacing.sm, paddingBottom: tokens.spacing.md, paddingTop: tokens.spacing.md },
  nutritionLabel: { color: tokens.color.textMuted, flex: 1, fontSize: 14, lineHeight: 20 },
  nutritionLabelEmphasis: { color: tokens.color.textMain, fontWeight: tokens.weight.bold },
  nutritionInputSurface: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, flexDirection: "row", height: 32, minWidth: 112, paddingHorizontal: tokens.spacing.sm },
  nutritionInput: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, height: 30, padding: 0, textAlign: "right" },
  nutritionUnit: { color: tokens.color.textSoft, fontSize: 12, marginLeft: 5 },
  confirmationHeading: { gap: tokens.spacing.xs },
  confirmationSubtitle: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  retentionPanel: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.panel, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.card.outerPadding },
  retentionRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  retentionCopy: { flex: 1, gap: tokens.spacing.xs },
  retentionTitle: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  retentionDetail: { color: tokens.color.textMuted, fontSize: 11, lineHeight: 16 },
  successHero: { alignItems: "center", gap: tokens.spacing.sm, paddingVertical: tokens.spacing.lg },
  successIcon: { alignItems: "center", borderRadius: 32, height: 64, justifyContent: "center", width: 64 },
  successTitle: { color: tokens.color.textMain, fontSize: 24, fontWeight: tokens.weight.extraBold, marginTop: tokens.spacing.sm, textAlign: "center" },
  successDetail: { color: tokens.color.textMuted, fontSize: tokens.type.caption, textAlign: "center" },
});
