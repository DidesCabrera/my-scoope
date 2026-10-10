import {
  Camera,
  Check,
  CheckCheck,
  ChevronLeft,
  ScanLine,
  ShieldCheck,
} from "lucide-react-native";
import { useState, type ReactNode } from "react";
import { Pressable, StyleSheet, Text, TextInput, View, type StyleProp, type ViewStyle } from "react-native";
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from "react-native-svg";

import { Button, DistributedTabBar, EntityIcon, Field, InlineNotice, MacroLoadingIndicator, Pill, SectionHeading } from "@/components/ui";
import { AssistantCreditBalance } from "@/components/assistant/assistant-credit-balance";
import { AnimatedScanBeam } from "@/components/label-capture/animated-scan-beam";
import { NutritionEntityCard } from "@/components/nutrition";
import { tokens } from "@/design/tokens";

export const labelCaptureStoryboardSteps = [
  { key: "intro", label: "Inicio y consentimiento" },
  { key: "camera", label: "Encuadre y captura" },
  { key: "preview", label: "Control de legibilidad" },
  { key: "processing", label: "Digitalización" },
  { key: "review", label: "Revisión de valores" },
  { key: "confirmation", label: "Confirmación final" },
  { key: "saved", label: "Alimento creado" },
] as const;

export type LabelCaptureStoryboardStep = (typeof labelCaptureStoryboardSteps)[number]["key"];

const noop = () => undefined;

const navigationTitles: Record<LabelCaptureStoryboardStep, string> = {
  intro: "",
  camera: "Tomar foto",
  preview: "Confirmación calidad",
  processing: "Analizando información",
  review: "Revisión de información",
  confirmation: "Crear Alimento",
  saved: "",
};

const navigationActions: Record<LabelCaptureStoryboardStep, { leading: "back" | null; trailing: "Cancelar" | "Listo" | null }> = {
  intro: { leading: "back", trailing: null },
  camera: { leading: "back", trailing: "Cancelar" },
  preview: { leading: "back", trailing: "Cancelar" },
  processing: { leading: null, trailing: null },
  review: { leading: null, trailing: "Cancelar" },
  confirmation: { leading: "back", trailing: "Cancelar" },
  saved: { leading: null, trailing: "Listo" },
};

function StoryboardNavigationHeader({ step }: { step: LabelCaptureStoryboardStep }) {
  const title = navigationTitles[step];
  const actions = navigationActions[step];

  return (
    <View accessibilityLabel={title ? `Encabezado de ${title}` : "Encabezado sin título"} style={styles.navigationHeader}>
      <View style={[styles.navigationSide, styles.navigationLeadingSide]}>
        {actions.leading === "back" ? (
          <Pressable accessibilityLabel="Volver" accessibilityRole="button" hitSlop={8} onPress={noop} style={({ pressed }) => pressed && styles.navigationActionPressed}>
            <ChevronLeft color={tokens.color.textMuted} size={26} strokeWidth={2.2} />
          </Pressable>
        ) : null}
      </View>
      <View style={styles.navigationIdentity}>
        {title ? <Text numberOfLines={1} style={styles.navigationTitle}>{title}</Text> : null}
      </View>
      <View style={styles.navigationSide}>
        {actions.trailing ? (
          <Pressable
            accessibilityHint={actions.trailing === "Listo" ? "Regresa a la pantalla que abrió Digitalizar" : "Regresa al inicio de Digitalizar etiqueta"}
            accessibilityLabel={actions.trailing}
            accessibilityRole="button"
            hitSlop={8}
            onPress={noop}
            style={({ pressed }) => pressed && styles.navigationActionPressed}>
            <Text numberOfLines={1} style={styles.navigationActionText}>{actions.trailing}</Text>
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

function StoryboardHeader({ detail, hideEyebrow = false, icon, title }: { detail?: string; hideEyebrow?: boolean; icon?: ReactNode; title: string }) {
  return (
    <View style={styles.headerBlock}>
      {icon ? <View style={styles.headerIcon}>{icon}</View> : null}
      {!hideEyebrow ? <Text style={styles.eyebrow}>DIGITALIZAR ETIQUETA</Text> : null}
      <Text style={styles.title}>{title}</Text>
      {detail ? <Text style={styles.description}>{detail}</Text> : null}
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

function FullBleedSquare({ children, surfaceStyle }: { children: ReactNode; surfaceStyle?: StyleProp<ViewStyle> }) {
  const [contentWidth, setContentWidth] = useState(0);
  const size = contentWidth ? contentWidth + tokens.spacing.screen * 2 : undefined;

  return (
    <View
      onLayout={({ nativeEvent }) => setContentWidth(nativeEvent.layout.width)}
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
      style={styles.cameraGuide}>
      {size.width > 4 && size.height > 4 ? (
        <Svg aria-hidden height={size.height} width={size.width}>
          <Defs>
            <LinearGradient id="label-capture-credit-guide" x1="0" x2="1" y1="0" y2="1">
              <Stop offset="0" stopColor={tokens.color.protein} />
              <Stop offset="0.5" stopColor={tokens.color.carbs} />
              <Stop offset="1" stopColor={tokens.color.fat} />
            </LinearGradient>
          </Defs>
          <Rect
            fill="none"
            height={size.height - 4}
            rx={tokens.radius.lg}
            ry={tokens.radius.lg}
            stroke="url(#label-capture-credit-guide)"
            strokeWidth="4"
            width={size.width - 4}
            x="2"
            y="2"
          />
        </Svg>
      ) : null}
    </View>
  );
}

function NutritionLabelMock({ compact = false, edgeToEdge = false }: { compact?: boolean; edgeToEdge?: boolean }) {
  return (
    <View accessibilityLabel="Ejemplo de fotografía de una etiqueta nutricional" style={[styles.photo, compact && styles.photoCompact, edgeToEdge && styles.photoEdgeToEdge]}>
      <View style={styles.photoGlow} />
      <View style={[styles.labelSheet, compact && styles.labelSheetCompact]}>
        <Text style={styles.labelHeading}>INFORMACIÓN NUTRICIONAL</Text>
        <Text style={styles.labelServing}>Porción: 1 envase (160 g)</Text>
        <View style={styles.labelRuleStrong} />
        <View style={styles.labelRow}><Text style={styles.labelTextStrong}>Por 100 g</Text><Text style={styles.labelTextStrong}>Cantidad</Text></View>
        <View style={styles.labelRule} />
        <View style={styles.labelRow}><Text style={styles.labelText}>Energía</Text><Text style={styles.labelText}>97 kcal</Text></View>
        <View style={styles.labelRow}><Text style={styles.labelText}>Proteínas</Text><Text style={styles.labelText}>9,0 g</Text></View>
        <View style={styles.labelRow}><Text style={styles.labelText}>Carbohidratos</Text><Text style={styles.labelText}>3,8 g</Text></View>
        <View style={styles.labelRow}><Text style={styles.labelText}>Grasas totales</Text><Text style={styles.labelText}>5,0 g</Text></View>
        <View style={styles.labelRow}><Text style={styles.labelText}>Sodio</Text><Text style={styles.labelText}>58 mg</Text></View>
      </View>
    </View>
  );
}

function IntroView() {
  return (
    <>
      <StoryboardHeader detail="Fotografía la tabla nutricional y crea un alimento privado sin transcribir cada dato." icon={<Camera color={tokens.color.textMain} size={34} strokeWidth={1.8} />} title="Convierte una etiqueta en segundos" />
      <View style={styles.introInfo}>
        <View style={styles.assuranceList}>
          <View style={styles.assuranceRow}><Camera color={tokens.color.textMuted} size={17} /><Text style={styles.assuranceText}>Captura o elige una foto clara.</Text></View>
          <View style={styles.assuranceRow}><ShieldCheck color={tokens.color.textMuted} size={17} /><Text style={styles.assuranceText}>Validamos nitidez antes de usar créditos.</Text></View>
          <View style={styles.assuranceRow}><Check color={tokens.color.textMuted} size={17} /><Text style={styles.assuranceText}>Tú confirmas cada valor antes de guardar.</Text></View>
        </View>
      </View>
      <InlineNotice>Enviaremos una copia reducida y sin metadatos para extraer los valores. La fotografía original no se guarda.</InlineNotice>
      <View style={styles.introBottom}>
        <AssistantCreditBalance availability={{ available_credits: 12 }} contained />
        <View style={styles.actionGroup}>
          <Button label="Abrir cámara" onPress={noop} />
          <Button label="Elegir desde galería" onPress={noop} variant="secondary" />
          <Button label="Ingresar manualmente" onPress={noop} variant="secondary" />
        </View>
      </View>
    </>
  );
}

function CameraView() {
  return (
    <>
      <FullBleedSquare surfaceStyle={styles.cameraFrame}>
        <NutritionLabelMock compact edgeToEdge />
        <CreditFocusGuide />
        <View style={styles.focusBadge}><ScanLine color={tokens.color.textMain} size={15} /><Text style={styles.focusText}>Enfoque listo</Text></View>
      </FullBleedSquare>
      <View style={[styles.confidenceNotice, styles.cameraHintNotice]}>
        <Text style={styles.confidenceNoticeText}>Intenta tomar la foto con buena iluminación y sin movimiento. Una mejor calidad de la foto facilitará un mejor resultado.</Text>
      </View>
      <View style={styles.bottomActions}>
        <Button label="Capturar foto" onPress={noop} />
        <View style={styles.cameraUtilityRow}>
          <Button label="Cambiar lente" onPress={noop} variant="secondary" />
          <Button label="Encender luz" onPress={noop} variant="secondary" />
        </View>
      </View>
    </>
  );
}

function PreviewView() {
  return (
    <>
      <FullBleedSquare><NutritionLabelMock edgeToEdge /></FullBleedSquare>
      <View style={styles.qualityPanel}>
        <View style={styles.qualityRow}>
          <View style={styles.qualityCopy}><Text style={styles.qualityTitle}>Lista para digitalizar</Text><Text style={styles.qualityDetail}>La fotografía superó las comprobaciones de nitidez, encuadre y perspectiva. El encabezado y todas las filas están visibles.</Text></View>
          <Pill color={tokens.color.success} label="Óptima" />
        </View>
      </View>
      <View style={styles.bottomActions}>
        <View style={styles.retentionPanel}>
          <View style={styles.retentionRow}>
            <View style={styles.qualityCopy}><Text style={styles.qualityTitle}>Autorizar análisis con OpenAI</Text><Text style={styles.qualityDetail}>Se enviará temporalmente esta copia reducida y sin metadatos para extraer los valores.</Text></View>
            <View style={styles.toggle}><View style={styles.toggleKnob} /></View>
          </View>
        </View>
        <Button label="Enviar a OpenAI y digitalizar · 1 crédito" onPress={noop} />
        <Button label="Tomar otra foto" onPress={noop} variant="secondary" />
      </View>
    </>
  );
}

function ProcessingView() {
  return (
    <>
      <FullBleedSquare surfaceStyle={styles.processingVisual}>
        <NutritionLabelMock compact edgeToEdge />
        <AnimatedScanBeam gradientId="label-capture-credit-scan" />
      </FullBleedSquare>
      <View style={styles.processingDetails}>
        <View style={styles.processingHeader}>
          <View style={styles.qualityCopy}><Text style={styles.processingTitle}>Analizando valores</Text><Text style={styles.qualityDetail}>Normalizando la información a 100 g.</Text></View>
          <MacroLoadingIndicator accessibilityLabel="Analizando los valores nutricionales" style={styles.processingLoading} />
        </View>
        <View style={styles.taskList}>
          <View style={styles.taskRow}><CreditTaskIcon complete id="credit-task-text" /><Text style={styles.taskDone}>Texto reconocido</Text></View>
          <View style={styles.taskRow}><CreditTaskIcon complete id="credit-task-column" /><Text style={styles.taskDone}>Columna por 100 g identificada</Text></View>
          <View style={styles.taskRow}><CreditTaskIcon complete={false} id="credit-task-nutrients" /><Text style={styles.taskActive}>Comprobando nutrientes…</Text></View>
        </View>
      </View>
      <Text style={styles.quietCenter}>No cierres esta pantalla. Suele tardar pocos segundos.</Text>
    </>
  );
}

const values = [
  { emphasized: true, label: "Proteínas", value: "9,0", unit: "g" },
  { emphasized: true, label: "Grasas totales", value: "5,0", unit: "g" },
  { label: "Grasas saturadas", value: "3,1", unit: "g" },
  { emphasized: true, label: "Carbohidratos", value: "3,8", unit: "g" },
  { label: "Azúcares", value: "3,8", unit: "g" },
  { label: "Fibra", value: "0", unit: "g" },
  { label: "Sodio", value: "58", unit: "mg" },
] as const;

function ReviewView() {
  return (
    <>
      <View style={styles.reviewEvidenceGroup}>
        <View accessibilityLabel="Fotografía fija con zoom y desplazamiento" style={styles.reviewEvidence}>
          <FullBleedSquare surfaceStyle={styles.reviewPhoto}>
            <NutritionLabelMock compact edgeToEdge />
          </FullBleedSquare>
        </View>
        <View style={styles.confidenceNotice}><Text style={styles.confidenceNoticeText}>La foto permanece fija mientras desplazas los valores. Confianza alta.</Text></View>
      </View>
      <View style={styles.reviewForm}>
        <DistributedTabBar<"g" | "ml">
          accessibilityLabel="Unidad de porción"
          activeTab="g"
          bleed
          onChange={noop}
          tabs={[{ key: "g", label: "Gramos" }, { key: "ml", label: "Mililitros" }]}
        />
        <View style={styles.reviewTitleRow}><Text style={styles.reviewTitle}>Valores por 100 g</Text></View>
        <View style={styles.nutritionRows}>
          {values.map((item) => (
            <View key={item.label} style={styles.nutritionRow}>
              <Text style={[styles.nutritionLabel, "emphasized" in item && item.emphasized && styles.nutritionLabelEmphasis]}>{item.label}</Text>
              <View style={styles.nutritionInputSurface}>
                <TextInput accessibilityLabel={item.label} defaultValue={item.value} keyboardType="decimal-pad" selectTextOnFocus style={styles.nutritionInput} />
                <Text style={styles.nutritionUnit}>{item.unit}</Text>
              </View>
            </View>
          ))}
          <View style={[styles.nutritionRow, styles.nutritionRowLast, styles.portionRow]}>
            <Text style={[styles.nutritionLabel, styles.nutritionLabelEmphasis]}>Tamaño de la porción</Text>
            <View style={styles.nutritionInputSurface}>
              <TextInput accessibilityLabel="Tamaño de la porción" defaultValue="160" keyboardType="decimal-pad" selectTextOnFocus style={styles.nutritionInput} />
              <Text style={styles.nutritionUnit}>g</Text>
            </View>
          </View>
        </View>
        <Field autoCapitalize="words" label="Nombre del producto" labelIcon={<EntityIcon entity="food" size="compact" />} labelStyle={styles.fieldLabel} onChangeText={noop} value="Yogur griego natural" />
      </View>
      <View style={styles.reviewContinue}><Button label="Continuar" onPress={noop} /></View>
    </>
  );
}

function ConfirmationView() {
  return (
    <>
      <View style={styles.confirmationHeading}>
        <SectionHeading icon={<CheckCheck color={tokens.color.entityIconForeground} size={18} />} title="Confirma el alimento" />
        <Text style={styles.confirmationSubtitle}>Al guardar confirmas que comparaste los valores con la etiqueta.</Text>
      </View>
      <NutritionEntityCard
        entity="food"
        indicators={[{ label: "base nutricional", value: "100 g" }]}
        nutrition={{
          calories: 97,
          carbs: { grams: 3.8, allocation: 16 },
          fat: { grams: 5, allocation: 47 },
          protein: { grams: 9, allocation: 37, perKilogram: 0.1 },
        }}
        title="Yogur griego natural"
      />
      <View style={styles.retentionPanel}>
        <View style={styles.retentionRow}><View style={styles.qualityCopy}><Text style={styles.qualityTitle}>Guardar copia procesada</Text><Text style={styles.qualityDetail}>Opcional, privada y eliminable después.</Text></View><View style={styles.toggle}><View style={styles.toggleKnob} /></View></View>
      </View>
      <View style={styles.bottomActions}>
        <Button label="Confirmar y crear alimento" onPress={noop} />
        <Button label="Volver a revisar" onPress={noop} variant="secondary" />
      </View>
    </>
  );
}

function SavedView() {
  return (
    <>
      <View style={styles.successHero}>
        <View style={styles.successIcon}>
          <Svg aria-hidden height="100%" pointerEvents="none" style={StyleSheet.absoluteFill} viewBox="0 0 64 64" width="100%">
            <Defs>
              <LinearGradient id="label-capture-success-credit" x1="0" x2="1" y1="0" y2="1">
                <Stop offset="0" stopColor={tokens.color.protein} />
                <Stop offset="0.5" stopColor={tokens.color.carbs} />
                <Stop offset="1" stopColor={tokens.color.fat} />
              </LinearGradient>
            </Defs>
            <Circle cx="32" cy="32" fill="url(#label-capture-success-credit)" r="32" />
          </Svg>
          <Check color={tokens.color.surfaceApp} size={32} />
        </View>
        <Text style={styles.successTitle}>Yogur griego natural</Text><Text style={styles.successDetail}>Creado en tu biblioteca privada</Text>
      </View>
      <NutritionEntityCard
        entity="food"
        indicators={[{ label: "base nutricional", value: "100 g" }]}
        nutrition={{
          calories: 97,
          carbs: { grams: 3.8, allocation: 16 },
          fat: { grams: 5, allocation: 47 },
          protein: { grams: 9, allocation: 37, perKilogram: 0.1 },
        }}
        title="Yogur griego natural"
      />
      <InlineNotice>La fotografía utilizada para la lectura no fue guardada.</InlineNotice>
      <View style={styles.bottomActions}>
        <Button label="Ver alimento" onPress={noop} />
        <Button label="Digitalizar otra etiqueta" onPress={noop} variant="secondary" />
      </View>
    </>
  );
}

const views: Record<LabelCaptureStoryboardStep, () => ReactNode> = {
  intro: IntroView,
  camera: CameraView,
  preview: PreviewView,
  processing: ProcessingView,
  review: ReviewView,
  confirmation: ConfirmationView,
  saved: SavedView,
};

export function LabelCaptureStoryboardView({ step }: { step: LabelCaptureStoryboardStep }) {
  const ViewComponent = views[step];
  return <View style={styles.screen}><StoryboardNavigationHeader step={step} /><ViewComponent /></View>;
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, gap: tokens.spacing.lg, minHeight: 760, paddingBottom: tokens.spacing.xl, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  navigationHeader: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", height: 48, justifyContent: "space-between", marginHorizontal: -tokens.spacing.screen, marginTop: -tokens.spacing.lg },
  navigationSide: { alignItems: "center", height: 48, justifyContent: "center", paddingHorizontal: tokens.spacing.sm, width: 92 },
  navigationLeadingSide: { alignItems: "flex-start", paddingLeft: tokens.spacing.lg },
  navigationIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "center", minWidth: 0 },
  navigationActionPressed: { opacity: 0.7 },
  navigationActionText: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  navigationTitle: { color: tokens.color.textMain, flexShrink: 1, fontSize: 16, fontWeight: tokens.weight.semibold, lineHeight: 22 },
  headerBlock: { alignItems: "flex-start", gap: tokens.spacing.sm },
  headerIcon: { marginBottom: tokens.spacing.md },
  eyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, letterSpacing: 1.2 },
  title: { color: tokens.color.textMain, fontSize: 27, fontWeight: tokens.weight.extraBold, letterSpacing: -0.7, lineHeight: 32 },
  description: { color: tokens.color.textMain, fontSize: tokens.type.body, lineHeight: 22, marginTop: tokens.spacing.sm },
  introInfo: { gap: tokens.card.gap },
  assuranceList: { gap: tokens.spacing.sm, marginTop: tokens.spacing.xs },
  assuranceRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  assuranceText: { color: tokens.color.textMuted, flex: 1, fontSize: tokens.type.caption, lineHeight: 19 },
  introBottom: { gap: tokens.spacing.sm, marginTop: "auto" },
  actionGroup: { gap: tokens.spacing.sm },
  bottomActions: { gap: tokens.spacing.sm, marginTop: "auto" },
  fullBleedSquareLayout: { marginTop: -tokens.spacing.lg, position: "relative" },
  fullBleedSquareFallback: { aspectRatio: 1 },
  fullBleedSquareSurface: { left: -tokens.spacing.screen, overflow: "hidden", position: "absolute", top: 0 },
  fullBleedSquareSurfaceFallback: { bottom: 0, right: -tokens.spacing.screen },
  photo: { alignItems: "center", backgroundColor: "#18202A", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.card, borderWidth: 1, height: 330, justifyContent: "center", overflow: "hidden", padding: tokens.spacing.lg },
  photoCompact: { height: 250 },
  photoEdgeToEdge: { aspectRatio: 1, borderLeftWidth: 0, borderRadius: 0, borderRightWidth: 0, height: "auto", width: "100%" },
  photoGlow: { backgroundColor: "rgba(255,255,255,0.08)", borderRadius: 160, height: 300, position: "absolute", width: 300 },
  labelSheet: { backgroundColor: "#F4F1E8", borderRadius: 4, gap: 5, padding: 14, transform: [{ rotate: "-1deg" }], width: "86%" },
  labelSheetCompact: { gap: 3, padding: 10, width: "80%" },
  labelHeading: { color: "#111", fontSize: 13, fontWeight: "900", letterSpacing: 0.2 },
  labelServing: { color: "#222", fontSize: 9 },
  labelRuleStrong: { backgroundColor: "#111", height: 4 },
  labelRule: { backgroundColor: "#111", height: 1 },
  labelRow: { flexDirection: "row", justifyContent: "space-between" },
  labelText: { color: "#222", fontSize: 9 },
  labelTextStrong: { color: "#111", fontSize: 9, fontWeight: "800" },
  cameraFrame: { backgroundColor: "#0C1118", borderBottomColor: tokens.color.borderDefault, borderBottomWidth: 1, borderTopColor: tokens.color.borderDefault, borderTopWidth: 1, justifyContent: "center" },
  cameraGuide: { aspectRatio: 1, borderRadius: tokens.radius.lg, left: 22, overflow: "hidden", position: "absolute", right: 22, top: 22 },
  focusBadge: { alignItems: "center", alignSelf: "center", backgroundColor: "rgba(5,10,15,0.86)", borderRadius: tokens.radius.pill, flexDirection: "row", gap: 6, paddingHorizontal: 12, paddingVertical: 7, position: "absolute", top: 46 },
  focusText: { color: tokens.color.textMain, fontSize: 11, fontWeight: tokens.weight.bold },
  cameraHintNotice: { marginTop: -tokens.spacing.lg },
  cameraUtilityRow: { gap: tokens.spacing.sm },
  qualityPanel: { backgroundColor: tokens.color.surfaceCard, marginHorizontal: -tokens.spacing.screen, marginTop: -tokens.spacing.lg, padding: tokens.card.outerPadding },
  qualityRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  qualityCopy: { flex: 1, gap: 2 },
  qualityTitle: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  qualityDetail: { color: tokens.color.textMuted, fontSize: 11, lineHeight: 16 },
  processingVisual: { position: "relative" },
  processingDetails: { gap: tokens.spacing.sm },
  processingHeader: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  processingLoading: { flexShrink: 0, marginLeft: -16, marginRight: 2, transform: [{ translateX: 16 }, { scale: 0.6 }] },
  processingTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.bold, lineHeight: 25 },
  taskList: { gap: tokens.spacing.sm, marginTop: tokens.spacing.sm, paddingTop: tokens.spacing.md },
  taskRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  taskDone: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  taskActive: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  quietCenter: { color: tokens.color.textSoft, fontSize: 11, lineHeight: 16, marginTop: 20, textAlign: "center" },
  reviewEvidence: { gap: 0 },
  reviewEvidenceGroup: { gap: 0 },
  reviewForm: { gap: tokens.card.gap, marginTop: tokens.spacing.sm },
  reviewContinue: { marginTop: tokens.spacing.lg },
  reviewPhoto: { position: "relative" },
  confidenceNotice: { backgroundColor: tokens.color.surfaceCard, marginHorizontal: -tokens.spacing.screen, paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  confidenceNoticeText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  reviewTitleRow: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  reviewTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.extraBold },
  nutritionRows: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, marginTop: -tokens.spacing.xs },
  nutritionRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 46, paddingLeft: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  nutritionRowLast: { borderBottomWidth: 0 },
  portionRow: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, marginTop: tokens.spacing.sm, paddingBottom: tokens.spacing.md, paddingTop: tokens.spacing.md },
  fieldLabel: { color: tokens.color.textMain },
  nutritionLabel: { color: tokens.color.textMain, flex: 1, fontSize: 14, lineHeight: 20 },
  nutritionLabelEmphasis: { fontWeight: tokens.weight.bold },
  nutritionInputSurface: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, flexDirection: "row", height: 32, minWidth: 112, paddingHorizontal: tokens.spacing.sm },
  nutritionInput: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, height: 30, padding: 0, textAlign: "right" },
  nutritionUnit: { color: tokens.color.textSoft, fontSize: 12, marginLeft: 5 },
  retentionPanel: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.panel, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.card.outerPadding },
  confirmationHeading: { gap: tokens.spacing.xs },
  confirmationSubtitle: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  retentionRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  toggle: { backgroundColor: tokens.color.borderStrong, borderRadius: tokens.radius.pill, height: 28, padding: 3, width: 48 },
  toggleKnob: { backgroundColor: tokens.color.textMain, borderRadius: 11, height: 22, width: 22 },
  successHero: { alignItems: "center", gap: tokens.spacing.sm, paddingVertical: tokens.spacing.lg },
  successIcon: { alignItems: "center", backgroundColor: tokens.color.success, borderRadius: 32, height: 64, justifyContent: "center", width: 64 },
  successTitle: { color: tokens.color.textMain, fontSize: 24, fontWeight: tokens.weight.extraBold, marginTop: tokens.spacing.sm, textAlign: "center" },
  successDetail: { color: tokens.color.textMuted, fontSize: tokens.type.caption, textAlign: "center" },
});
