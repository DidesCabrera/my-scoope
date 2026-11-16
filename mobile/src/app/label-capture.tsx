import * as Crypto from "expo-crypto";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import * as Linking from "expo-linking";
import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { Camera, Check, CheckCheck, ChevronsDown, ChevronsUp, ScanLine } from "lucide-react-native";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Image, Keyboard, Modal, Platform, Pressable, StyleSheet, Text, TextInput, View, type StyleProp, type ViewStyle } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from "react-native-reanimated";
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from "react-native-svg";

import { userFacingError } from "@/api/errors";
import type { EntitlementsData } from "@/api/billing-types";
import { useSession } from "@/auth/session-context";
import { CreditDashboardGrid } from "@/components/assistant/credit-dashboard-grid";
import { AnimatedScanBeam } from "@/components/label-capture/animated-scan-beam";
import { HalfHeightScrollablePhoto } from "@/components/label-capture/half-height-scrollable-photo";
import { HouseholdEquivalencePicker } from "@/components/libraries/household-equivalence-picker";
import { householdMeasures, type HouseholdMeasure } from "@/components/libraries/household-equivalence-picker.types";
import { householdMeasureDisplayLabel } from "@/components/pickers/food-portion-nutrition";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { NutritionEntityCard } from "@/components/nutrition";
import { Button, Card, DistributedTabBar, Field, InlineNotice, MacroLoadingIndicator, NutritionFactsCard, Screen, SectionHeading, SectionTitle, StatusFeedbackModal, SystemSwitch, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { appConfig } from "@/config/app-config";
import {
  LABEL_CAMERA_AUTOFOCUS,
  LABEL_CAMERA_FOCUS_SETTLE_MS,
} from "@/label-capture/camera";
import { deleteCachedImage, prepareLabelImage, type PreparedLabelImage } from "@/label-capture/image";
import { loadLabelCapturePreferences, saveLabelCapturePreferences, type LabelCapturePreferences } from "@/label-capture/preferences";
import {
  classifyLabelImageQuality,
  nextLabelCaptureStep,
  recognizeLabelWithOneRetry,
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

type Phase = "intro" | "camera" | "captured" | "preview" | "processing" | "review" | "confirmation" | "saved";
type CaptureSource = "camera" | "gallery";
type QualityValidationFailure = "module_unavailable" | "recognition_failed" | "platform_unsupported" | null;
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
  householdAmount: string;
  householdMeasure: HouseholdMeasure;
  householdDetail: string;
  volumeWeight: string;
};

const emptyForm: FormState = {
  name: "", energy: "", protein: "", carbs: "", fat: "", saturatedFat: "",
  sugar: "", fiber: "", sodium: "", servingSize: "", householdAmount: "1", householdMeasure: "", householdDetail: "", volumeWeight: "",
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

function validSuggestedPortion(form: FormState): boolean {
  const portion = optionalNumber(form.servingSize);
  if (form.servingSize.trim() && (!portion || portion > 10_000)) return false;
  if (!form.householdMeasure) return true;
  const amount = optionalNumber(form.householdAmount);
  return Boolean(portion && amount && amount <= 100
    && (form.householdMeasure !== "other" || (form.householdDetail.trim().length > 0 && form.householdDetail.trim().length <= 100)));
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

function FullBleedSquare({ children, surfaceStyle, verticalCrop = 0 }: { children: ReactNode; surfaceStyle?: StyleProp<ViewStyle>; verticalCrop?: number }) {
  const [contentWidth, setContentWidth] = useState(0);
  const size = contentWidth ? contentWidth + tokens.spacing.screen * 2 : undefined;
  const croppedHeight = size ? size * (1 - verticalCrop) : undefined;
  const cropOffset = size ? -(size * verticalCrop / 2) : undefined;
  return (
    <View
      onLayout={({ nativeEvent }) => setContentWidth((current) => current === nativeEvent.layout.width ? current : nativeEvent.layout.width)}
      style={[styles.fullBleedSquareLayout, verticalCrop > 0 && styles.fullBleedSquareCropped, size ? { height: croppedHeight } : styles.fullBleedSquareFallback]}>
      <View style={[surfaceStyle, styles.fullBleedSquareSurface, size ? { height: size, top: cropOffset, width: size } : styles.fullBleedSquareSurfaceFallback]}>{children}</View>
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
  const validationInFlightRef = useRef(false);
  const { status, session, apiRequest } = useSession();
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
  const [planName, setPlanName] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [prepared, setPrepared] = useState<PreparedLabelImage | null>(null);
  const [photoCollapsed, setPhotoCollapsed] = useState(false);
  const [localCandidate, setLocalCandidate] = useState<LocalCandidate | undefined>();
  const [imageQuality, setImageQuality] = useState<LabelImageQuality>(unavailableLabelImageQuality);
  const [qualityValidationFailure, setQualityValidationFailure] = useState<QualityValidationFailure>(null);
  const [qualityConfidence, setQualityConfidence] = useState<number | null>(null);
  const [savePhotographs, setSavePhotographs] = useState(false);
  const [shareForCuration, setShareForCuration] = useState(false);
  const [aiConsentGranted, setAiConsentGranted] = useState<boolean | null>(null);
  const [validateBeforeSending, setValidateBeforeSending] = useState(true);
  const [preferencesUserId, setPreferencesUserId] = useState<number | null>(null);
  const preferencesReady = Boolean(session?.user_id && preferencesUserId === session.user_id);
  const [preferenceSaving, setPreferenceSaving] = useState(false);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [consentDialog, setConsentDialog] = useState(false);
  const [qualityResultNotice, setQualityResultNotice] = useState<"suitable" | "unsuitable" | null>(null);
  const validatorAvailable = Platform.OS === "ios" && isNutritionLabelOcrAvailable();
  const [captureSource, setCaptureSource] = useState<CaptureSource>("camera");
  const [error, setError] = useState<string | null>(null);
  const [captureKey, setCaptureKey] = useState(Crypto.randomUUID());
  const [keyboardVisible, setKeyboardVisible] = useState(false);

  useEffect(() => {
    if (!qualityResultNotice) return;
    const timer = setTimeout(() => setQualityResultNotice(null), qualityResultNotice === "suitable" ? 900 : 1800);
    return () => clearTimeout(timer);
  }, [qualityResultNotice]);

  useEffect(() => {
    if (!session?.user_id) return;
    let active = true;
    void loadLabelCapturePreferences(session.user_id).then((preferences) => {
      if (!active) return;
      setAiConsentGranted(preferences.aiConsentGranted);
      setValidateBeforeSending(validatorAvailable && preferences.validateBeforeSending);
      setSavePhotographs(preferences.savePhotographs);
      setShareForCuration(preferences.shareForCuration);
    }).catch(() => {
      if (active) setValidateBeforeSending(validatorAvailable);
    }).finally(() => { if (active) setPreferencesUserId(session.user_id); });
    return () => { active = false; };
  }, [session?.user_id, validatorAvailable]);

  async function changePreference(patch: Partial<LabelCapturePreferences>): Promise<boolean> {
    if (!preferencesReady || preferenceSaving || !session?.user_id) return false;
    const next = { aiConsentGranted, validateBeforeSending, savePhotographs, shareForCuration, ...patch };
    setAiConsentGranted(next.aiConsentGranted);
    setValidateBeforeSending(next.validateBeforeSending);
    setSavePhotographs(next.savePhotographs);
    setShareForCuration(next.shareForCuration);
    setPreferenceSaving(true);
    try {
      await saveLabelCapturePreferences(session.user_id, next);
      return true;
    } catch {
      setError("No pudimos guardar esta preferencia. Vuelve a intentarlo.");
      setAiConsentGranted(aiConsentGranted);
      setValidateBeforeSending(validateBeforeSending);
      setSavePhotographs(savePhotographs);
      setShareForCuration(shareForCuration);
      return false;
    } finally {
      setPreferenceSaving(false);
    }
  }

  useEffect(() => {
    if (status !== "authenticated") return;
    void apiRequest<FoodLabelAIConfig>("/api/v1/foods/label-captures/config")
      .then(setConfig)
      .catch(() => setConfig(null));
    void apiRequest<EntitlementsData>("/api/v1/entitlements")
      .then((entitlements) => setPlanName(entitlements.plan_name))
      .catch(() => setPlanName(null));
  }, [apiRequest, status]);

  useEffect(() => () => deleteCachedImage(prepared?.uri), [prepared?.uri]);
  useEffect(() => () => {
    if (cameraReadyTimerRef.current) clearTimeout(cameraReadyTimerRef.current);
  }, []);
  useEffect(() => {
    const showEvent = Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const hideEvent = Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide";
    const showSubscription = Keyboard.addListener(showEvent, () => setKeyboardVisible(true));
    const hideSubscription = Keyboard.addListener(hideEvent, () => setKeyboardVisible(false));
    return () => {
      showSubscription.remove();
      hideSubscription.remove();
    };
  }, []);

  function update(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function applyDraft(next: NutritionLabelDraft, name = "", detected?: FoodLabelAIAnalysis) {
    setDraft(next);
    const displayedValues = next.normalizationStatus === "ready" ? next.values : next.sourceValues;
    setForm((current) => ({
      ...emptyForm,
      householdAmount: detected ? valueString(detected.household_amount) || "1" : current.householdAmount,
      householdMeasure: detected ? (householdMeasures.some(({ value }) => value === detected.household_measure) ? detected.household_measure as HouseholdMeasure : "") : current.householdMeasure,
      householdDetail: detected ? detected.household_detail || "" : current.householdDetail,
      name,
      energy: valueString(displayedValues.energy_kcal),
      protein: valueString(displayedValues.protein_g),
      carbs: valueString(displayedValues.carbs_g),
      fat: valueString(displayedValues.fat_g),
      saturatedFat: valueString(displayedValues.saturated_fat_g),
      sugar: valueString(displayedValues.sugar_g),
      fiber: valueString(displayedValues.fiber_g),
      sodium: valueString(displayedValues.sodium_mg),
      servingSize: detected ? valueString(next.basis === "per_100ml" ? detected.serving_size_ml : next.servingSizeG) : current.servingSize,
    }));
    setPhase("review");
  }

  function confirmBasis(basis: "per_100g" | "per_serving" | "per_100ml") {
    if (!draft) return;
    try {
      applyDraft(confirmNutritionLabelBasis(draft, basis), form.name);
      if ((draft.basis === "per_100ml") !== (basis === "per_100ml")) {
        setForm((current) => ({ ...current, servingSize: "", householdAmount: "1", householdMeasure: "", householdDetail: "" }));
      }
      setError(null);
    } catch {
      setError("No pudimos confirmar la base de esta etiqueta.");
    }
  }

  function setReviewUnit(unit: "g" | "ml") {
    if (!draft) return;
    const basis = unit === "ml" ? "per_100ml" : "per_100g";
    if (draft.normalizationStatus !== "ready") {
      confirmBasis(basis);
      return;
    }
    setDraft((current) => current ? { ...current, basis } : current);
    if ((draft.basis === "per_100ml") !== (basis === "per_100ml")) {
      setForm((current) => ({ ...current, servingSize: "", householdAmount: "1", householdMeasure: "", householdDetail: "" }));
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
    setForm(emptyForm);
    deleteCachedImage(prepared?.uri);
    setPrepared(null);
    setPhotoCollapsed(false);
    setLocalCandidate(undefined);
    setImageQuality(unavailableLabelImageQuality);
    setQualityConfidence(null);
    setAnalysisId(null);
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

  async function prepareForPreview(uri: string, width: number, height: number, source: CaptureSource) {
    setPreparing(true);
    setError(null);
    let nextPrepared: PreparedLabelImage | null = null;
    try {
      const preparedImage = await prepareLabelImage(uri, width, height);
      nextPrepared = preparedImage;
      setCaptureKey(Crypto.randomUUID());
      setPrepared(nextPrepared);
      setCaptureSource(source);
      setPhotoCollapsed(false);
      setLocalCandidate(undefined);
      setImageQuality(unavailableLabelImageQuality);
      setQualityValidationFailure(null);
      setQualityConfidence(null);
      setAnalysisId(null);
      setPhase("captured");
    } catch (nextError) {
      deleteCachedImage(nextPrepared?.uri);
      setError(`No pudimos preparar esta foto. ${userFacingError(nextError)}`);
      setPhase("intro");
    } finally {
      deleteCachedImage(uri);
      setPreparing(false);
    }
  }

  async function validateAndAnalyze(image = prepared, consentApproved = aiConsentGranted === true) {
    if (!image || !consentApproved || validationInFlightRef.current || analysisInFlightRef.current) return;
    validationInFlightRef.current = true;
    setProcessing(true);
    setError(null);
    let nextLocalCandidate: LocalCandidate | undefined;
    let nextImageQuality = unavailableLabelImageQuality;
    let nextQualityValidationFailure: QualityValidationFailure = null;
    if (validateBeforeSending) {
      if (Platform.OS !== "ios") nextQualityValidationFailure = "platform_unsupported";
      else if (!isNutritionLabelOcrAvailable()) nextQualityValidationFailure = "module_unavailable";
      else {
        try {
          const recognition = await recognizeLabelWithOneRetry(() => recognizeNutritionLabel(image.uri));
          const local = normalizeNutritionLabel(recognition);
          nextLocalCandidate = { basis: local.basis, values: local.values as Record<string, number> };
          nextImageQuality = classifyLabelImageQuality(recognition.imageQuality);
        } catch {
          nextQualityValidationFailure = "recognition_failed";
        }
      }
    }
    setLocalCandidate(nextLocalCandidate);
    setImageQuality(nextImageQuality);
    setQualityValidationFailure(nextQualityValidationFailure);
    const nextStep = nextLabelCaptureStep(validateBeforeSending, nextImageQuality.status);
    validationInFlightRef.current = false;
    setProcessing(false);
    if (nextStep === "retake") {
      deleteCachedImage(image.uri);
      setPrepared(null);
      setPhase(captureSource === "camera" ? "camera" : "intro");
      setError(null);
      setQualityResultNotice("unsuitable");
    } else if (nextStep === "review") {
      setPhase("preview");
    } else {
      if (validateBeforeSending && nextImageQuality.status === "suitable") setQualityResultNotice("suitable");
      await analyzePreparedImage(image, captureKey, nextLocalCandidate, consentApproved);
    }
  }

  function startDigitization() {
    if (!prepared || !preferencesReady || preferenceSaving || processing) return;
    if (aiConsentGranted === null) { setConsentDialog(true); return; }
    if (!aiConsentGranted) { setSettingsVisible(true); return; }
    void validateAndAnalyze(prepared);
  }

  async function analyzePreparedImage(image = prepared, key = captureKey, candidate = localCandidate, consentApproved = aiConsentGranted === true) {
    if (!image || !consentApproved || analysisInFlightRef.current) return;
    analysisInFlightRef.current = true;
    setProcessing(true);
    setError(null);
    setPhase("processing");
    try {
      const result = await apiRequest<FoodLabelAIAnalysis>("/api/v1/foods/label-captures/analyze", {
        method: "POST",
        body: JSON.stringify({
          image_base64: image.base64,
          image_content_type: image.contentType,
          image_width: image.width,
          image_height: image.height,
          idempotency_key: key,
          consent_to_ai_processing: true,
          local_candidate: candidate,
        }),
      });
      setAnalysisId(result.analysis_id);
      setQualityConfidence(result.quality_confidence);
      setConfig((current) => current ? { ...current, available_credits: result.available_credits } : current);
      applyDraft(aiDraft(result), result.name, result);
    } catch (nextError) {
      setError(`${userFacingError(nextError)} Puedes usar otra foto o completar los valores manualmente sin consumir una digitalización fallida.`);
      setPhase("captured");
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
      await prepareForPreview(photo.uri, photo.width, photo.height, "camera");
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
        await prepareForPreview(asset.uri, asset.width, asset.height, "gallery");
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

  const retakePhoto = useCallback(() => {
    deleteCachedImage(prepared?.uri);
    setPrepared(null);
    setPhotoCollapsed(false);
    setLocalCandidate(undefined);
    setImageQuality(unavailableLabelImageQuality);
    if (captureSource === "gallery") setPhase("intro");
    else {
      setCameraReady(false);
      setTorchEnabled(false);
      setPhase("camera");
    }
  }, [captureSource, prepared?.uri]);

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
    if (!validSuggestedPortion(form)) {
      setError("Revisa la porción sugerida y su equivalencia cotidiana.");
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
    if (!validSuggestedPortion(form)) {
      setError("Revisa la porción sugerida y su equivalencia cotidiana.");
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
      serving_size_g: portionUnit === "g" ? optionalNumber(form.servingSize) : undefined,
      default_portion: optionalNumber(form.servingSize),
      household_amount: form.householdMeasure ? optionalNumber(form.householdAmount) : undefined,
      household_measure: form.householdMeasure,
      household_detail: form.householdMeasure === "other" ? form.householdDetail.trim() : "",
      volume_weight_g_per_100ml: undefined,
      declared_energy_kcal_per_100g: optionalNumber(form.energy),
      detected_basis: draft?.basis ?? "manual",
      ocr_engine: draft?.ocrEngine ?? "manual_entry",
      ocr_engine_version: draft?.ocrEngineVersion ?? "1",
      field_confidence: draft?.fieldConfidence ?? {},
      warnings: draft?.warnings ?? ["manual_review"],
      idempotency_key: captureKey,
      analysis_id: analysisId ?? undefined,
      retain_label_image: Boolean(savePhotographs && prepared && analysisId),
      share_for_curation: Boolean(shareForCuration && prepared && analysisId),
      label_image_base64: savePhotographs || shareForCuration ? prepared?.base64 : undefined,
      label_image_content_type: savePhotographs || shareForCuration ? prepared?.contentType : undefined,
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
    setPhotoCollapsed(false);
    setLocalCandidate(undefined);
    setImageQuality(unavailableLabelImageQuality);
    setQualityConfidence(null);
    setAnalysisId(null);
    setConsentDialog(false);
    setSettingsVisible(false);
    setQualityResultNotice(null);
    setError(null);
    setCaptureKey(Crypto.randomUUID());
    setCaptureSource("camera");
    setPhase("intro");
  }, [prepared?.uri]);

  useFocusEffect(useCallback(() => {
    const hiddenLeadingAction = { icon: "none" as const, label: "", onPress: () => undefined };
    if (phase === "intro") {
      setHeaderPresentation({ action: { icon: "settings", label: "Configuración de digitalización", onPress: () => setSettingsVisible(true) }, fallback: "/today", mode: "back", title: "Digitalizar etiqueta" });
    } else if (phase === "camera") {
      setHeaderPresentation({ action: { label: "Cancelar", onPress: restart }, leadingAction: { icon: "back", label: "Volver", onPress: restart }, mode: "back", title: "Tomar foto" });
    } else if (phase === "captured") {
      setHeaderPresentation({ action: { icon: "settings", label: "Configuración de digitalización", onPress: () => setSettingsVisible(true) }, leadingAction: { icon: "back", label: "Volver", onPress: () => void retakePhoto() }, mode: "back", title: "Fotografía capturada" });
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
  }, [captureSource, phase, restart, retakePhoto, router, setHeaderPresentation]));

  const settingsModal = (
    <Modal animationType="fade" onRequestClose={() => setSettingsVisible(false)} transparent visible={settingsVisible}>
      <View style={styles.qualityDialogBackdrop}>
        <View style={styles.qualityDialogCard}>
          <Text style={styles.qualityDialogTitle}>Configuración de digitalización</Text>
          <View style={styles.settingsRows}>
            <View style={styles.retentionRow}>
              <View style={styles.retentionCopy}>
                <Text style={styles.retentionTitle}>Validación previa de fotografía</Text>
                <Text style={styles.retentionDetail}>{validatorAvailable ? "Revisa la calidad en el iPhone antes de enviarla." : "Este dispositivo o instalación no tiene disponible la validación previa."}</Text>
              </View>
              <SystemSwitch accessibilityLabel="Validación previa de fotografía" disabled={!preferencesReady || preferenceSaving || !validatorAvailable} onValueChange={(value) => { void changePreference({ validateBeforeSending: value }); }} value={preferencesReady && validatorAvailable && validateBeforeSending} />
            </View>
            <View style={styles.retentionRow}>
              <View style={styles.retentionCopy}>
                <Text style={styles.retentionTitle}>Autorizar análisis con OpenAI</Text>
                <Text style={styles.retentionDetail}>Se enviará una copia reducida y sin metadatos para extraer los valores. Consulta la <Text accessibilityRole="link" onPress={() => void Linking.openURL(`${appConfig.apiBaseUrl}/privacy/`).catch((nextError) => setError(userFacingError(nextError)))} style={{ textDecorationLine: "underline" }}>política de privacidad</Text>.</Text>
              </View>
              <SystemSwitch accessibilityLabel="Autorizar análisis con OpenAI" disabled={!preferencesReady || preferenceSaving} onValueChange={(value) => { void changePreference({ aiConsentGranted: value }); }} value={aiConsentGranted === true} />
            </View>
            <View style={styles.retentionRow}>
              <View style={styles.retentionCopy}><Text style={styles.retentionTitle}>Guardar fotografías</Text><Text style={styles.retentionDetail}>Guarda una copia procesada junto a cada alimento digitalizado.</Text></View>
              <SystemSwitch accessibilityLabel="Guardar fotografías" disabled={!preferencesReady || preferenceSaving} onValueChange={(value) => { void changePreference({ savePhotographs: value }); }} value={savePhotographs} />
            </View>
            <View style={styles.retentionRow}>
              <View style={styles.retentionCopy}><Text style={styles.retentionTitle}>Compartir información para mejorar la base de datos de My Scoope</Text><Text style={styles.retentionDetail}>Envía la foto sin metadatos y los valores confirmados para revisión. No se publican automáticamente. Al desactivar esta opción, se detienen solo los envíos futuros.</Text></View>
              <SystemSwitch accessibilityLabel="Compartir información para mejorar la base de datos de My Scoope" disabled={!preferencesReady || preferenceSaving} onValueChange={(value) => { void changePreference({ shareForCuration: value }); }} value={shareForCuration} />
            </View>
          </View>
          <Button disabled={preferenceSaving} label="Cerrar" onPress={() => setSettingsVisible(false)} variant="secondary" />
        </View>
      </View>
    </Modal>
  );

  const consentModal = (
    <Modal animationType="fade" onRequestClose={() => setConsentDialog(false)} transparent visible={consentDialog}>
      <View style={styles.qualityDialogBackdrop}>
        <View style={styles.qualityDialogCard}>
          <Text style={styles.qualityDialogTitle}>Autorizar análisis con OpenAI</Text>
          <Text style={styles.qualityDialogDescription}>Para digitalizar la etiqueta enviaremos a OpenAI una copia reducida de la fotografía, sin metadatos. La fotografía original no se guarda. Puedes cambiar esta decisión en Configuración de digitalización.</Text>
          <Button disabled={preferenceSaving} label="Autorizar y continuar" loading={preferenceSaving} onPress={() => { void changePreference({ aiConsentGranted: true }).then((saved) => { if (saved) { setConsentDialog(false); void validateAndAnalyze(prepared, true); } }); }} />
          <Button disabled={preferenceSaving} label="Ahora no" onPress={() => { void changePreference({ aiConsentGranted: false }).then((saved) => { if (saved) setConsentDialog(false); }); }} variant="secondary" />
        </View>
      </View>
    </Modal>
  );

  const qualityResultModal = <StatusFeedbackModal label={qualityResultNotice === "suitable" ? "Esta imagen es óptima para digitalización" : "Esta imagen no es apta"} tone={qualityResultNotice === "suitable" ? "success" : "error"} visible={qualityResultNotice !== null} />;

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
            onCameraReady={cameraDidBecomeReady}
            onMountError={() => { setPhase("intro"); setError("No pudimos iniciar la cámara. Puedes elegir una foto de tu galería."); }}
            ref={cameraRef}
            style={StyleSheet.absoluteFill}
            zoom={0}
          />
          <CreditFocusGuide />
          <View pointerEvents="none" style={styles.focusBadge}>
            <ScanLine color={tokens.color.textMain} size={15} />
            <Text style={styles.focusText}>{cameraReady ? "Enfoque listo" : "Preparando enfoque"}</Text>
          </View>
        </FullBleedSquare>
        <Text style={styles.capturedTitle}>Para un mejor resultado</Text>
        <Text style={styles.capturedDetail}>Intenta tomar la fotografía con buena iluminación y sin movimiento.</Text>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <View style={styles.bottomActions}>
          <Button disabled={!cameraReady || capturing || preparing} label="Capturar foto" loading={capturing || preparing} onPress={() => void capture()} />
          <Button disabled={!cameraReady || capturing || preparing} label={torchEnabled ? "Apagar luz" : "Encender luz"} onPress={() => setTorchEnabled((current) => !current)} variant="secondary" />
        </View>
        {qualityResultModal}
      </Screen>
    );
  }

  if (phase === "captured" && prepared) {
    return (
      <Screen
        fixedHeader={<FullBleedSquare><Image accessibilityLabel="Fotografía capturada de la etiqueta nutricional" resizeMode="contain" source={{ uri: prepared.uri }} style={StyleSheet.absoluteFill} /></FullBleedSquare>}
        fixedHeaderStyle={styles.photoFixedHeader}
        headerMode="preserve"
        scroll={false}>
        <Text style={styles.capturedTitle}>Revisa la fotografía</Text>
        <Text style={styles.capturedDetail}>Comprueba que la tabla nutricional esté completa y se pueda leer.</Text>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <View style={styles.bottomActions}>
          <Button disabled={!preferencesReady || preferenceSaving || processing} label="Digitalizar información" loading={processing} onPress={startDigitization} />
          <Button disabled={processing} label="Tomar otra foto" onPress={() => void retakePhoto()} variant="secondary" />
        </View>
        {settingsModal}
        {consentModal}
      </Screen>
    );
  }

  if (phase === "preview" && prepared) {
    return (
      <Screen
        fixedHeader={<FullBleedSquare><Image accessibilityLabel="Fotografía procesada de la etiqueta nutricional" resizeMode="contain" source={{ uri: prepared.uri }} style={StyleSheet.absoluteFill} /></FullBleedSquare>}
        fixedHeaderStyle={styles.photoFixedHeader}
        headerMode="preserve"
        scroll={false}>
        <Text style={styles.capturedTitle}>Comprueba la fotografía</Text>
        <Text style={styles.capturedDetail}>{imageQuality.status === "reviewable"
          ? "La foto podría leerse, pero conviene revisar nitidez y encuadre antes de usar una digitalización."
          : qualityValidationFailure === "recognition_failed"
            ? "La validación previa no pudo completarse tras dos intentos. Puedes continuar si la etiqueta se ve completa y legible."
            : "La validación previa no está disponible en este dispositivo o instalación. Puedes continuar si la etiqueta se ve completa y legible."}</Text>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <View style={styles.bottomActions}>
          <Button disabled={processing} label="Continuar y digitalizar" loading={processing} onPress={() => void analyzePreparedImage()} />
          <Button disabled={processing} label="Tomar otra foto" onPress={() => void retakePhoto()} variant="secondary" />
        </View>
      </Screen>
    );
  }

  if (phase === "processing" && prepared) {
    return (
      <Screen
        fixedHeader={<FullBleedSquare surfaceStyle={styles.processingPhoto}>
          <Image accessibilityLabel="Etiqueta nutricional en análisis" resizeMode="contain" source={{ uri: prepared.uri }} style={StyleSheet.absoluteFill} />
          <AnimatedScanBeam gradientId="label-capture-live-scan" />
        </FullBleedSquare>}
        fixedHeaderStyle={styles.photoFixedHeader}
        headerMode="preserve"
        scroll={false}>
        <View style={styles.processingDetails}>
          <View style={styles.processingHeader}>
            <Text style={styles.processingTitle}>Analizando valores</Text>
            <MacroLoadingIndicator accessibilityLabel="Analizando los valores nutricionales" style={styles.processingLoading} />
          </View>
          <View style={styles.taskList}>
            <View style={styles.taskRow}><CreditTaskIcon complete id="live-credit-task-text" /><Text style={styles.taskDone}>Texto reconocido</Text></View>
            <View style={styles.taskRow}><CreditTaskIcon complete id="live-credit-task-column" /><Text style={styles.taskDone}>Columna nutricional identificada</Text></View>
            <View style={styles.taskRow}><CreditTaskIcon complete={false} id="live-credit-task-nutrients" /><Text style={styles.taskActive}>Comprobando nutrientes…</Text></View>
          </View>
        </View>
        {qualityResultModal}
      </Screen>
    );
  }

  const formNutrition = nutritionSummary(
    optionalNumber(form.protein) ?? 0,
    optionalNumber(form.carbs) ?? 0,
    optionalNumber(form.fat) ?? 0,
    optionalNumber(form.energy),
  );

  const nutrientRows: { emphasized?: boolean; field: keyof FormState; label: string; unit: string }[] = [
    { emphasized: true, field: "protein", label: "Proteínas", unit: "g" },
    { emphasized: true, field: "fat", label: "Grasas totales", unit: "g" },
    { field: "saturatedFat", label: "Grasas saturadas", unit: "g" },
    { emphasized: true, field: "carbs", label: "Carbohidratos", unit: "g" },
    { field: "sugar", label: "Azúcares", unit: "g" },
    { field: "fiber", label: "Fibra", unit: "g" },
    { field: "sodium", label: "Sodio", unit: "mg" },
  ];
  const portionUnit = draft?.basis === "per_100ml" ? "ml" : "g";
  const suggestedPortion = optionalNumber(form.servingSize);
  const householdAmount = optionalNumber(form.householdAmount);

  return (
    <Screen
      contentStyle={phase === "review" && prepared ? styles.reviewScrollContent : undefined}
      fixedHeader={phase === "review" && prepared ? (
        <View style={styles.reviewPhotoExpanded}>
          {photoCollapsed ? (
            <HalfHeightScrollablePhoto surfaceStyle={styles.reviewPhoto}>
              <Image accessibilityLabel="Etiqueta nutricional analizada" resizeMode="contain" source={{ uri: prepared.uri }} style={StyleSheet.absoluteFill} />
            </HalfHeightScrollablePhoto>
          ) : (
            <FullBleedSquare surfaceStyle={styles.reviewPhoto} verticalCrop={keyboardVisible ? 0.2 : 0}>
              <ZoomableLabelImage accessibilityLabel="Etiqueta nutricional analizada" uri={prepared.uri} />
            </FullBleedSquare>
          )}
          <Pressable accessibilityLabel={photoCollapsed ? "Expandir imagen de la etiqueta" : "Contraer imagen de la etiqueta"} accessibilityRole="button" hitSlop={4} onPress={() => setPhotoCollapsed((current) => !current)} style={[styles.reviewPhotoAction, styles.reviewPhotoCollapseAction]} testID={photoCollapsed ? "label-photo-expand" : "label-photo-collapse"}>
            {photoCollapsed ? <ChevronsDown color={tokens.color.textMain} size={18} /> : <ChevronsUp color={tokens.color.textMain} size={18} />}
          </Pressable>
        </View>
      ) : undefined}
      fixedHeaderStyle={styles.photoFixedHeader}
      headerMode="preserve"
    >
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}

      {phase === "intro" ? (
        <>
          <View style={styles.introHeader}>
            <Camera color={tokens.color.textMain} size={34} strokeWidth={1.8} />
            <Text style={styles.eyebrow}>DIGITALIZAR INFORMACIÓN NUTRICIONAL</Text>
            <Text style={styles.introTitle}>Enriquece tu librería personal de alimentos</Text>
            <Text style={styles.introDescription}>Fotografía la tabla nutricional y crea un alimento privado sin transcribir cada dato.</Text>
          </View>
          <Image accessible={false} resizeMode="contain" source={require("../../assets/images/nutrition-label-illustration-450.png")} style={styles.introIllustration} />
          <View style={styles.introBottom}>
            {config ? <CreditDashboardGrid availableCredits={config.available_credits} planName={planName ?? config.plan_name} /> : null}
            <View style={styles.actionGroup}>
              <Button disabled={config ? !config.can_scan : false} label="Abrir cámara" loading={openingCamera} onPress={() => void beginCamera()} />
              <Button disabled={config ? !config.can_scan : false} label="Elegir desde galería" loading={preparing} onPress={() => void chooseFromGallery()} variant="secondary" />
              <Button label="Ingresar manualmente" onPress={() => beginManualReview()} variant="secondary" />
            </View>
          </View>
          {settingsModal}
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
              <Field keyboardType="decimal-pad" label="Peso de la porción (g)" labelStyle={styles.fieldLabel} onChangeText={(value) => update("servingSize", value)} value={form.servingSize} />
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
            <View style={styles.measurementTabs}>
              <Text style={styles.measurementLabel}>Métrica de medición del alimento</Text>
              <DistributedTabBar<"g" | "ml">
                accessibilityLabel="Unidad de porción"
                activeTab={portionUnit}
                bleed
                onChange={setReviewUnit}
                tabs={[{ key: "g", label: "Gramos" }, { key: "ml", label: "Mililitros" }]}
              />
            </View>
            <Text style={styles.reviewTitle}>{draft?.normalizationStatus === "ready" ? `Valores por 100 ${draft.basis === "per_100ml" ? "ml" : "g"}` : "Valores extraídos"}</Text>
            <View style={styles.nutritionRows}>
              {nutrientRows.map((item) => (
                <View key={item.field} style={styles.nutritionRow}>
                  <Text style={[styles.nutritionLabel, item.emphasized && styles.nutritionLabelEmphasis]}>{item.label}</Text>
                  <View style={styles.nutritionInputSurface}>
                    <TextInput accessibilityLabel={item.label} keyboardType="decimal-pad" onChangeText={(value) => update(item.field, value)} selectTextOnFocus style={styles.nutritionInput} value={form[item.field]} />
                    <Text style={styles.nutritionUnit}>{item.unit}</Text>
                  </View>
                </View>
              ))}
            </View>
            <View style={styles.suggestedPortionSection}>
              <Text style={styles.reviewTitle}>Porción sugerida</Text>
              <Text style={textStyles.caption}>El selector de comidas usará esta cantidad como punto de partida.</Text>
              <View style={styles.suggestedPortionAmount}>
                <Field keyboardType="decimal-pad" label={`Cantidad en ${portionUnit}`} labelStyle={styles.fieldLabel} onChangeText={(value) => update("servingSize", value)} placeholder={`Ej: 150 ${portionUnit}`} value={form.servingSize} />
              </View>
              <Text style={styles.equivalenceLabel}>Equivalencia cotidiana (opcional)</Text>
              <HouseholdEquivalencePicker amount={form.householdAmount} measure={form.householdMeasure} onAmountChange={(value) => update("householdAmount", value)} onMeasureChange={(value) => update("householdMeasure", value)} />
              {form.householdMeasure === "other" ? <Field label="Nombre de la medida" maxLength={100} onChangeText={(value) => update("householdDetail", value)} placeholder="Ej: cucharón" value={form.householdDetail} /> : null}
              {form.householdMeasure && suggestedPortion && householdAmount ? <Text style={textStyles.caption}>{householdAmount.toLocaleString("es-CL")} {householdMeasureDisplayLabel(form.householdMeasure === "other" ? form.householdDetail.trim() || "medida" : householdMeasures.find(({ value }) => value === form.householdMeasure)?.label ?? "medida", householdAmount)} = {suggestedPortion.toLocaleString("es-CL")} {portionUnit}</Text> : null}
            </View>
            <View style={styles.productNameField}>
              <Field autoCapitalize="words" label="Nombre del producto" labelStyle={styles.fieldLabel} onChangeText={(value) => update("name", value)} placeholder="Ej. Yogur griego natural" value={form.name} />
            </View>
          </View>
          <View style={styles.reviewContinue}><Button label="Continuar" onPress={continueToConfirmation} /></View>
        </>
      ) : null}

      {phase === "confirmation" ? (
        <>
          <View style={styles.confirmationHeading}>
            <SectionHeading icon={<CheckCheck color={tokens.color.entityIconForeground} size={18} />} title="Confirma el alimento" />
          </View>
          <NutritionEntityCard collapsiblePanel entity="food" indicators={[{ label: "base nutricional", value: `100 ${portionUnit}` }]} nutrition={formNutrition} title={form.name.trim() || "Alimento sin nombre"}>
            <NutritionFactsCard
              facts={{
                carbsG: optionalNumber(form.carbs) ?? null,
                fiberG: optionalNumber(form.fiber) ?? null,
                proteinG: optionalNumber(form.protein) ?? null,
                saturatedFatG: optionalNumber(form.saturatedFat) ?? null,
                sodiumMg: optionalNumber(form.sodium) ?? null,
                sugarG: optionalNumber(form.sugar) ?? null,
                totalFatG: optionalNumber(form.fat) ?? null,
              }}
              portion={{ quantity: optionalNumber(form.servingSize) ?? null, unit: portionUnit }}
            />
          </NutritionEntityCard>
          <View style={styles.bottomActions}>
            <Button label="Confirmar creación" loading={saving} onPress={() => void save()} />
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
          <InlineNotice>{saved.label_image_retained ? "Guardamos una copia procesada junto a tu alimento." : "No guardamos una copia junto a tu alimento privado."}{saved.shared_for_curation ? " También enviamos la foto sin metadatos y los valores confirmados para revisión del catálogo." : ""}</InlineNotice>
          <View style={styles.bottomActions}>
            <Button label="Ver alimento" onPress={() => router.push(`/libraries/foods/${saved.id}` as Href)} />
            <Button label="Digitalizar otra etiqueta" onPress={restart} variant="secondary" />
          </View>
        </>
      ) : null}

      {qualityResultModal}

    </Screen>
  );
}

const styles = StyleSheet.create({
  fixedScreen: { flexGrow: 1, paddingBottom: tokens.spacing.lg },
  fullBleedSquareLayout: { marginTop: -tokens.spacing.lg, position: "relative" },
  fullBleedSquareCropped: { overflow: "hidden" },
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
  qualityDialogBackdrop: { alignItems: "center", backgroundColor: "rgba(0,0,0,0.7)", flex: 1, justifyContent: "center", padding: tokens.spacing.screen },
  qualityDialogCard: { backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.panel, gap: tokens.spacing.md, padding: tokens.card.outerPadding, width: "100%" },
  qualityDialogTitle: { color: tokens.color.textMain, fontSize: 22, fontWeight: tokens.weight.bold },
  qualityDialogDescription: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 22 },
  capturedTitle: { color: tokens.color.textMain, fontSize: 22, fontWeight: tokens.weight.bold },
  capturedDetail: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 22 },
  qualityCopy: { flex: 1, gap: 2 },
  qualityDetail: { color: tokens.color.textMuted, fontSize: 11, lineHeight: 16 },
  processingPhoto: { position: "relative" },
  processingDetails: { gap: tokens.spacing.sm },
  processingHeader: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.sm },
  processingLoading: { flexShrink: 0, marginLeft: -16, marginRight: 2, transform: [{ translateX: 16 }, { scale: 0.6 }] },
  processingTitle: { color: tokens.color.textMain, flex: 1, fontSize: 22, fontWeight: tokens.weight.bold },
  taskList: { gap: tokens.spacing.sm },
  taskRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  taskDone: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  taskActive: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  introHeader: { alignItems: "flex-start", gap: tokens.spacing.sm },
  eyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, letterSpacing: 1.2, marginTop: tokens.spacing.md },
  introTitle: { color: tokens.color.textMain, fontSize: 27, fontWeight: tokens.weight.extraBold, letterSpacing: -0.7, lineHeight: 32 },
  introDescription: { color: tokens.color.textMain, fontSize: tokens.type.body, lineHeight: 22, marginTop: tokens.spacing.sm },
  introIllustration: { alignSelf: "center", height: 200, marginTop: tokens.spacing.md, width: "100%" },
  introBottom: { gap: tokens.spacing.sm, marginTop: "auto" },
  settingsRows: { gap: tokens.spacing.lg, paddingVertical: tokens.spacing.sm },
  actionGroup: { gap: tokens.spacing.sm },
  photoFixedHeader: { paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  reviewScrollContent: { paddingTop: 0 },
  reviewPhotoMessage: { backgroundColor: tokens.color.surfaceApp, marginTop: 0 },
  reviewPhoto: { backgroundColor: "#18202A", position: "relative" },
  reviewPhotoExpanded: { position: "relative" },
  reviewPhotoAction: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, height: 36, justifyContent: "center", width: 36 },
  reviewPhotoCollapseAction: { backgroundColor: "rgba(10, 10, 10, 0.82)", bottom: 12, position: "absolute", right: 12 - tokens.spacing.screen },
  warningList: { gap: tokens.spacing.xs },
  warningTitle: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  reviewForm: { gap: tokens.card.gap, marginTop: tokens.spacing.sm },
  measurementTabs: { gap: tokens.spacing.sm },
  measurementLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  reviewContinue: { marginTop: tokens.spacing.xl },
  reviewTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.extraBold },
  nutritionRows: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, marginTop: -tokens.spacing.xs },
  nutritionRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 46, paddingLeft: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  suggestedPortionSection: { gap: tokens.spacing.sm, marginTop: 12 },
  suggestedPortionAmount: { marginTop: 4 },
  equivalenceLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700", marginTop: 8 },
  productNameField: { marginTop: 4 },
  fieldLabel: { color: tokens.color.textMain },
  nutritionLabel: { color: tokens.color.textMain, flex: 1, fontSize: 14, lineHeight: 20 },
  nutritionLabelEmphasis: { fontWeight: tokens.weight.bold },
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
