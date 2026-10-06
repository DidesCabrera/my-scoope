import {
  Activity,
  ArrowRight,
  BarChart3,
  BookOpen,
  BrainCircuit,
  Check,
  ChevronLeft,
  CircleUserRound,
  Dumbbell,
  Eye,
  Gauge,
  HeartPulse,
  Layers3,
  Leaf,
  LockKeyhole,
  Scale,
  Sparkles,
  Target,
} from "lucide-react-native";
import { createContext, type ComponentType, type ReactNode, useContext, useMemo } from "react";
import { PanResponder, Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from "react-native-svg";

import { DailyPlanMealDetailList, type DailyPlanMealDetailItem, EntityDetailPage, EntityDetailSection } from "@/components/details";
import { NutritionKpiSection } from "@/components/nutrition";
import { EntityPanelTabs, MealPanels, type MealPanelItem, PanelSurface } from "@/components/panels";
import { ProposalDailyPlanCard } from "@/components/proposals/proposal-preview";
import { commercialPlanBenefits, SubscriptionPlanCard, SubscriptionPurchaseButton } from "@/components/subscriptions/subscription-plan-card";
import { Button, Card, Field, InlineNotice, MyScoopeLogo, Pill, textStyles } from "@/components/ui";
import type { OnboardingEstimate, ProposalDetail } from "@/api/types";
import { tokens } from "@/design/tokens";

export const onboardingJourneySteps = [
  { key: "login", shortLabel: "Acceso", label: "Acceso" },
  { key: "value", shortLabel: "Funciones", label: "Funciones principales" },
  { key: "structure", shortLabel: "Estructura", label: "Organización nutricional" },
  { key: "panels", shortLabel: "Paneles", label: "Lectura de paneles" },
  { key: "control", shortLabel: "Asistencia", label: "Asistencia y decisiones" },
  { key: "progress", shortLabel: "Progreso", label: "Seguimiento del progreso" },
  { key: "disclosures", shortLabel: "Límites", label: "Información y límites" },
  { key: "goal", shortLabel: "Objetivo", label: "Objetivo nutricional" },
  { key: "identity", shortLabel: "Datos", label: "Datos personales" },
  { key: "measurements", shortLabel: "Medidas", label: "Medidas corporales" },
  { key: "activity", shortLabel: "Actividad", label: "Actividad y entrenamiento" },
  { key: "dietary", shortLabel: "Preferencias", label: "Preferencias alimentarias" },
  { key: "summary", shortLabel: "Resumen", label: "Resumen de la ficha" },
  { key: "dailyPlan", shortLabel: "Plan", label: "Primer plan diario" },
  { key: "plans", shortLabel: "Planes", label: "Planes disponibles" },
] as const;

export type OnboardingJourneyStep = (typeof onboardingJourneySteps)[number]["key"];

const explanationSteps = onboardingJourneySteps.slice(1, 6);

export const onboardingNutritionFields = ["goal", "birth_date", "sex", "height_cm", "weight_kg", "activity_level", "training_frequency", "dietary_pattern", "allergies_or_intolerances", "avoided_foods"] as const;

type Icon = ComponentType<{ color?: string; size?: number; strokeWidth?: number }>;

const noop = () => undefined;

export type OnboardingJourneyValues = {
  goal: string;
  birthDate: string;
  sex: "male" | "female";
  height: string;
  weight: string;
  activityLevel: string;
  trainingFrequency: number;
  dietaryPattern: string;
  allergy: string;
  allergyDetails: string;
  avoidedFoods: string;
};

export type OnboardingJourneyController = {
  values: OnboardingJourneyValues;
  estimate?: OnboardingEstimate | null;
  proposal?: ProposalDetail | null;
  busy?: boolean;
  error?: string | null;
  onChange?(field: keyof OnboardingJourneyValues, value: string | number): void;
  onNext?(): void;
  onBack?(): void;
  onLogin?(): void;
  onAdjust?(): void;
  onChoosePlan?(plan: "Free" | "Basic" | "Pro"): void;
};

const galleryValues: OnboardingJourneyValues = {
  goal: "fat_loss",
  birthDate: "1990-05-10",
  sex: "male",
  height: "178",
  weight: "82,5",
  activityLevel: "light",
  trainingFrequency: 3,
  dietaryPattern: "omnivore",
  allergy: "",
  allergyDetails: "",
  avoidedFoods: "Cilantro y aceitunas",
};

const JourneyControllerContext = createContext<OnboardingJourneyController>({ values: galleryValues });

function useJourneyController() {
  return useContext(JourneyControllerContext);
}

function StepHeader({ brandedCentered = false, icon: IconComponent, index, eyebrow, title, description }: {
  brandedCentered?: boolean;
  description: string;
  eyebrow: string;
  icon: Icon;
  index: number;
  title: string;
}) {
  const isExplanation = index >= 1 && index <= 5;
  const isProfileStep = index >= 7 && index <= 12;
  const usesBrandedHeader = isExplanation || brandedCentered;
  const isCenteredIntro = index <= 12 || brandedCentered;
  const usesCenteredTitleSpacing = index <= 6 || brandedCentered;
  return (
    <View style={[styles.intro, isCenteredIntro && styles.introCentered]}>
      {usesBrandedHeader ? <View style={styles.centeredLogo}><MyScoopeLogo /></View> : isProfileStep ? <ProfileProgress index={index} /> : index === 6 ? null : (
        <View style={styles.stepMeta}>
          <Text style={styles.stepCount}>{String(index + 1).padStart(2, "0")} / {onboardingJourneySteps.length}</Text>
          <View accessibilityLabel={`Paso ${index + 1} de ${onboardingJourneySteps.length}`} style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${((index + 1) / onboardingJourneySteps.length) * 100}%` }]} />
          </View>
        </View>
      )}
      {!usesBrandedHeader ? <View style={styles.iconWell}><IconComponent color={tokens.color.entityIconForeground} size={27} strokeWidth={1.8} /></View> : null}
      {!usesBrandedHeader && !isProfileStep ? <Text style={[styles.eyebrow, isCenteredIntro && styles.centeredText, index === 6 && styles.disclosuresEyebrow]}>{eyebrow}</Text> : null}
      <Text style={[styles.title, isCenteredIntro && styles.centeredText, usesCenteredTitleSpacing && styles.centeredTitleSpacing]}>{title}</Text>
      {!isProfileStep ? <Text style={[styles.description, isCenteredIntro && styles.centeredText]}>{description}</Text> : null}
    </View>
  );
}

function ExplanationDots({ action, index }: { action?: ReactNode; index: number }) {
  const activeIndex = index - 1;
  return (
    <View style={[styles.explanationFooter, action ? styles.explanationFooterWithAction : null]}>
      <View accessibilityLabel={`Vista ${activeIndex + 1} de ${explanationSteps.length}`} style={styles.explanationDots}>
        {explanationSteps.map((step, dotIndex) => (
          <View
            key={step.key}
            accessibilityElementsHidden
            style={[styles.explanationDot, dotIndex === activeIndex && styles.explanationDotActive]}
          >
            {dotIndex === activeIndex ? (
              <Svg aria-hidden height="100%" viewBox="0 0 10 10" width="100%">
                <Defs>
                  <LinearGradient id="onboarding-credit-gradient" x1="0" x2="1" y1="0" y2="1">
                    <Stop offset="0" stopColor={tokens.color.protein} />
                    <Stop offset="0.5" stopColor={tokens.color.carbs} />
                    <Stop offset="1" stopColor={tokens.color.fat} />
                  </LinearGradient>
                </Defs>
                <Circle cx="5" cy="5" fill="url(#onboarding-credit-gradient)" r="5" />
              </Svg>
            ) : null}
          </View>
        ))}
      </View>
      {action}
    </View>
  );
}

function ContinueChip({ label = "Continuar", onPress }: { label?: string; onPress?: () => void }) {
  const controller = useJourneyController();
  return (
    <Pressable accessibilityRole="button" disabled={controller.busy} onPress={onPress ?? controller.onNext ?? noop} style={[styles.continueChip, controller.busy && styles.actionDisabled]}>
      <Svg aria-hidden pointerEvents="none" style={StyleSheet.absoluteFill}>
        <Defs>
          <LinearGradient id="continue-chip-border" x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Rect fill="url(#continue-chip-border)" height="100%" width="100%" />
      </Svg>
      <View style={styles.continueChipInset} />
      <Text style={styles.continueChipText}>{label}</Text>
    </Pressable>
  );
}

function CreditContinueButton({ chip = false, label = "Continuar", onPress }: { chip?: boolean; label?: string; onPress?: () => void }) {
  const controller = useJourneyController();
  return (
    <Pressable accessibilityRole="button" disabled={controller.busy} onPress={onPress ?? controller.onNext ?? noop} style={[styles.creditContinueButton, chip && styles.creditContinueButtonChip, controller.busy && styles.actionDisabled]}>
      <Svg aria-hidden pointerEvents="none" style={StyleSheet.absoluteFill}>
        <Defs>
          <LinearGradient id="daily-plan-credit-button" x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Rect fill="url(#daily-plan-credit-button)" height="100%" width="100%" />
      </Svg>
      <Text style={[styles.creditContinueLabel, chip && styles.creditContinueLabelChip]}>{label}</Text>
    </Pressable>
  );
}

function CreditSelectionBorder({ id, shape = "md" }: { id: string; shape?: "md" | "lg" | "pill" }) {
  const radius = shape === "pill" ? 17 : shape === "lg" ? tokens.radius.lg : tokens.radius.md;
  return (
    <Svg aria-hidden pointerEvents="none" style={StyleSheet.absoluteFill}>
      <Defs>
        <LinearGradient id={id} x1="0" x2="1" y1="0" y2="1">
          <Stop offset="0" stopColor={tokens.color.protein} />
          <Stop offset="0.5" stopColor={tokens.color.carbs} />
          <Stop offset="1" stopColor={tokens.color.fat} />
        </LinearGradient>
      </Defs>
      <Rect fill="none" height="100%" rx={radius} stroke={`url(#${id})`} strokeWidth="4" width="100%" />
    </Svg>
  );
}

function CreditSelectionCheck() {
  return (
    <View style={styles.goalSelectionCheck}>
      <Svg aria-hidden height="22" pointerEvents="none" viewBox="0 0 22 22" width="22">
        <Defs>
          <LinearGradient id="goal-selection-check" x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Path d="M3.5 11.5 8.5 16.5 18.5 6.5" fill="none" stroke="url(#goal-selection-check)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" />
      </Svg>
    </View>
  );
}

function SelectedActivityRadio() {
  return (
    <View style={[styles.radio, styles.radioSelected]}>
      <Svg aria-hidden height="100%" viewBox="0 0 20 20" width="100%">
        <Defs>
          <LinearGradient id="activity-radio-credit" x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Circle cx="10" cy="10" fill={tokens.color.surfaceElevated} r="9" stroke="url(#activity-radio-credit)" strokeWidth="2" />
        <Circle cx="10" cy="10" fill="url(#activity-radio-credit)" r="5" />
      </Svg>
    </View>
  );
}

function ProfileProgress({ index }: { index: number }) {
  const activeIndex = index - 7;
  const creditGradient = (shape: "dot" | "line", id: string) => (
    <Svg aria-hidden height="100%" viewBox={shape === "dot" ? "0 0 14 14" : "0 0 100 2"} width="100%">
      <Defs>
        <LinearGradient id={id} x1="0" x2="1" y1="0" y2="1">
          <Stop offset="0" stopColor={tokens.color.protein} />
          <Stop offset="0.5" stopColor={tokens.color.carbs} />
          <Stop offset="1" stopColor={tokens.color.fat} />
        </LinearGradient>
      </Defs>
      {shape === "dot" ? <Circle cx="7" cy="7" fill={`url(#${id})`} r="7" /> : <Rect fill={`url(#${id})`} height="2" width="100" />}
    </Svg>
  );
  return (
    <View style={styles.profileProgressGroup}>
      <Text style={[styles.profileProgressEyebrow, index >= 8 && styles.profileProgressEyebrowTextMain]}>OBJETIVO Y PLANIFICACIÓN</Text>
      <View accessibilityLabel={`Paso ${activeIndex + 1} de 6 de tu perfil`} style={styles.profileProgress}>
        {Array.from({ length: 6 }, (_, stepIndex) => (
          <View key={stepIndex} style={[styles.profileProgressItem, stepIndex === 5 && styles.profileProgressItemLast]}>
            <View style={styles.profileProgressDot}>
              {stepIndex <= activeIndex ? creditGradient("dot", `profile-dot-${stepIndex}`) : null}
            </View>
            {stepIndex < 5 ? (
              <View style={styles.profileProgressLine}>
                {stepIndex < activeIndex ? creditGradient("line", `profile-line-${stepIndex}`) : null}
              </View>
            ) : null}
          </View>
        ))}
      </View>
    </View>
  );
}

function JourneyFooter({ index, primary = "Continuar", secondary = "Atrás" }: { index: number; primary?: string; secondary?: string }) {
  const controller = useJourneyController();
  if (index >= 7 && index <= 12) {
    return (
      <View style={[styles.footer, styles.profileFooter]}>
        <Pressable accessibilityRole="button" disabled={controller.busy} onPress={controller.onBack ?? noop} style={[styles.backAction, styles.profileBackAction]}>
          <ChevronLeft color={tokens.color.textMuted} size={16} />
          <Text style={styles.backLabel}>{secondary}</Text>
        </Pressable>
        <View style={styles.profilePrimaryAction}>
          {index === 12 ? <CreditContinueButton chip label={primary} /> : <ContinueChip label={primary} />}
        </View>
      </View>
    );
  }
  return (
    <View style={styles.footer}>
      {index === 6 ? <CreditContinueButton label={primary} /> : <Button label={primary} loading={controller.busy} onPress={controller.onNext ?? noop} />}
      {index > 0 ? (
        <Pressable accessibilityRole="button" disabled={controller.busy} onPress={controller.onBack ?? noop} style={styles.backAction}>
          <ChevronLeft color={tokens.color.textMuted} size={16} />
          <Text style={styles.backLabel}>{secondary}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

function ExplanationCard({ icon: IconComponent, title, body }: { body: string; icon: Icon; title: string }) {
  return (
    <View style={styles.explanationCard}>
      <View style={styles.explanationIcon}><IconComponent color={tokens.color.entityIconForeground} size={18} /></View>
      <View style={styles.explanationCopy}>
        <Text style={styles.explanationTitle}>{title}</Text>
        <Text style={styles.explanationBody}>{body}</Text>
      </View>
    </View>
  );
}

function LoginView({ index }: { index: number }) {
  const controller = useJourneyController();
  return (
    <>
      <View style={styles.centeredLogo}><MyScoopeLogo /></View>
      <View accessibilityLabel={`Paso ${index + 1} de ${onboardingJourneySteps.length}`} style={styles.loginHero}>
        <Text style={styles.loginTitle}>Inicia sesión para guardar tu progreso</Text>
        <Text style={[textStyles.muted, styles.centeredText]}>Usa tu cuenta para continuar el proceso en cualquiera de tus dispositivos.</Text>
      </View>
      <View style={styles.loginAction}>
        <Button label="Iniciar sesión o crear cuenta" multicolorSurface="app" onPress={controller.onLogin ?? noop} variant="multicolor" />
      </View>
    </>
  );
}

function ValueView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="My Scoope organiza tu objetivo, calcula referencias nutricionales y las convierte en un plan diario que puedes revisar." eyebrow="Funciones principales" icon={Target} index={index} title="Qué puedes hacer con My Scoope" />
      <View style={styles.valueFeatures}>
        <ExplanationCard body="Una estructura diaria que puedes revisar, adaptar y ejecutar." icon={Check} title="Plan diario" />
        <ExplanationCard body="Calorías, macros y cantidades en una lectura ordenada." icon={Gauge} title="Referencias nutricionales" />
      </View>
      <ExplanationDots index={index} />
    </>
  );
}

function StructureView({ index }: { index: number }) {
  const levels = [
    { color: tokens.color.food, label: "Alimentos", detail: "La base nutricional" },
    { color: tokens.color.meal, label: "Comidas", detail: "Combinaciones que repites" },
    { color: tokens.color.dailyPlan, label: "Planes diarios", detail: "La pauta de un día" },
    { color: tokens.color.program, label: "Programas", detail: "Tu estrategia en el tiempo" },
  ];
  return (
    <>
      <StepHeader description="La información se organiza en cuatro niveles reutilizables: alimentos, comidas, planes diarios y programas." eyebrow="Estructura del sistema" icon={Layers3} index={index} title="Cómo se organiza tu alimentación" />
      <View style={styles.levels}>
        {levels.map((level, levelIndex) => (
          <View key={level.label} style={styles.levelRow}>
            <View style={[styles.levelMarker, { backgroundColor: level.color }]}><Text style={styles.levelNumber}>{levelIndex + 1}</Text></View>
            <View style={styles.levelCopy}><Text style={styles.levelTitle}>{level.label}</Text><Text style={styles.levelDetail}>{level.detail}</Text></View>
            {levelIndex < levels.length - 1 ? <ArrowRight color={tokens.color.textSoft} size={17} /> : <Check color={tokens.color.success} size={17} />}
          </View>
        ))}
      </View>
      <ExplanationDots index={index} />
    </>
  );
}

function PanelsView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="Cada panel muestra primero un resumen y permite consultar calorías, macronutrientes y detalle." eyebrow="Paneles de información" icon={Eye} index={index} title="Cómo leer los paneles" />
      <Card>
        <View style={styles.panelEntityHeader}>
          <View><Text style={styles.panelEyebrow}>PLAN DIARIO</Text><Text style={styles.panelEntityTitle}>Día equilibrado</Text></View>
          <Pill label="2.140 kcal" color={tokens.color.dailyPlan} />
        </View>
        <PanelSurface>
          <EntityPanelTabs activeTab="summary" onChange={noop} tabs={[
            { key: "summary", label: "Resumen" },
            { key: "calories", label: "Calorías" },
            { key: "macros", label: "Macros" },
            { key: "detail", label: "Detalle" },
          ]} />
          <View style={styles.panelPreview}>
            <Text style={styles.panelPreviewValue}>155 g</Text>
            <Text style={styles.panelPreviewLabel}>proteína para tu objetivo</Text>
            <View style={styles.panelBars}><View style={[styles.panelBar, { backgroundColor: tokens.color.protein, flex: 30 }]} /><View style={[styles.panelBar, { backgroundColor: tokens.color.carbs, flex: 44 }]} /><View style={[styles.panelBar, { backgroundColor: tokens.color.fat, flex: 26 }]} /></View>
          </View>
        </PanelSurface>
        <Text style={styles.panelHint}>Resumen primero. Evidencia y detalle a un toque.</Text>
      </Card>
      <ExplanationDots index={index} />
    </>
  );
}

function ControlView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="La asistencia interpreta tu solicitud y prepara una propuesta. Tú la revisas antes de aplicarla." eyebrow="Asistencia y control" icon={BrainCircuit} index={index} title="Cómo funciona la asistencia" />
      <View style={styles.controlFlow}>
        <ExplanationCard body="Explicas tu objetivo con tus propias palabras." icon={Sparkles} title="1. Conversa" />
        <ExplanationCard body="El sistema transforma la intención en objetivos revisables." icon={BarChart3} title="2. Calcula" />
        <ExplanationCard body="Nada importante cambia sin tu confirmación." icon={Check} title="3. Aprueba" />
      </View>
      <ExplanationDots index={index} />
    </>
  );
}

function ProgressView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="Compara lo planificado con tus registros para decidir si necesitas ajustar el plan." eyebrow="Seguimiento" icon={BarChart3} index={index} title="Cómo revisar tu progreso" />
      <Card>
        <View style={styles.metricRow}><Text style={styles.metricLabel}>Adherencia semanal</Text><Text style={styles.metricValue}>86%</Text></View>
        <View style={styles.metricTrack}><View style={styles.metricFill} /></View>
        <View style={styles.progressFacts}>
          <ExplanationCard body="Registro simple y cronológico." icon={Scale} title="Peso" />
          <ExplanationCard body="Revisiones que explican cambios." icon={Activity} title="Evolución" />
        </View>
      </Card>
      <ExplanationDots
        action={<ContinueChip />}
        index={index}
      />
    </>
  );
}

function DisclosuresView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="Revisa qué hace My Scoope, qué no hace y qué decisiones quedan bajo tu responsabilidad." eyebrow="Uso responsable" icon={LockKeyhole} index={index} title="Información importante antes de continuar" />
      <View style={styles.noticeStack}>
        <ExplanationCard body="No diagnostica, trata ni reemplaza atención profesional." icon={HeartPulse} title="No es atención médica" />
        <ExplanationCard body="Los cálculos y propuestas deben revisarse antes de usarse." icon={Eye} title="Revisa antes de aplicar" />
        <ExplanationCard body="Tú decides qué datos compartes y puedes eliminar tu cuenta." icon={LockKeyhole} title="Privacidad y control" />
      </View>
      <InlineNotice>Al continuar confirmas que comprendes estos límites. Podrás consultar las políticas completas cuando quieras.</InlineNotice>
      <JourneyFooter index={index} primary="Entiendo y quiero continuar" />
    </>
  );
}

function GoalView({ index }: { index: number }) {
  const controller = useJourneyController();
  const goals = [
    ["fat_loss", "Bajar grasa"],
    ["muscle_gain", "Ganar masa muscular"],
    ["maintenance", "Mantenerme"],
    ["performance", "Rendimiento deportivo"],
    ["healthy_eating", "Comer mejor"],
  ] as const;
  return (
    <>
      <StepHeader description="Tu objetivo orienta el ajuste energético y la referencia inicial de proteína. Siempre podrás cambiarlo." eyebrow="Objetivo nutricional" icon={Target} index={index} title="Define tu objetivo" />
      <View style={styles.optionGrid}>
        {goals.map(([value, label]) => {
          const selected = controller.values.goal === value;
          return (
            <Pressable accessibilityRole="radio" accessibilityState={{ selected }} key={value} onPress={() => controller.onChange?.("goal", value)} style={[styles.optionCard, selected && styles.optionCardSelected]}>
              {selected ? <CreditSelectionBorder id="goal-option-border" shape="lg" /> : null}
              <Text style={[styles.optionText, selected && styles.optionTextSelected]}>{label}</Text>
              {selected ? <CreditSelectionCheck /> : null}
            </Pressable>
          );
        })}
      </View>
      <JourneyFooter index={index} />
    </>
  );
}

function IdentityView({ index }: { index: number }) {
  const controller = useJourneyController();
  return (
    <>
      <StepHeader description="La edad y el sexo usado para el cálculo forman parte de la estimación de tu gasto basal." eyebrow="Datos para el cálculo" icon={CircleUserRound} index={index} title="Ingresa tus datos personales" />
      <Card style={styles.profileCard}>
        <Field inputStyle={styles.profileInput} label="Fecha de nacimiento" labelStyle={styles.profileQuestion} onChangeText={(value) => controller.onChange?.("birthDate", value)} placeholder="AAAA-MM-DD" value={controller.values.birthDate} />
        <View accessibilityRole="radiogroup" style={styles.identityChoiceField}>
          <Text style={styles.profileQuestion}>Sexo usado para el cálculo nutricional</Text>
          <View style={styles.identityChoiceRow}>
            {["Masculino", "Femenino"].map((label, optionIndex) => {
              const value = optionIndex === 0 ? "male" : "female";
              const selected = controller.values.sex === value;
              return (
                <Pressable accessibilityRole="radio" accessibilityState={{ selected }} key={label} onPress={() => controller.onChange?.("sex", value)} style={[styles.trainingFrequencyChip, selected && styles.identityChoiceSelected]}>
                  {selected ? <CreditSelectionBorder id="identity-option-border" shape="pill" /> : null}
                  <Text style={[styles.trainingFrequencyChipLabel, selected && styles.trainingFrequencyChipLabelSelected]}>{label}</Text>
                </Pressable>
              );
            })}
          </View>
        </View>
      </Card>
      <InlineNotice>Usamos estos datos para estimaciones nutricionales, no para definir tu identidad.</InlineNotice>
      <JourneyFooter index={index} />
    </>
  );
}

function MeasurementsView({ index }: { index: number }) {
  const controller = useJourneyController();
  return (
    <>
      <StepHeader description="La altura y el peso permiten estimar tu gasto energético y calcular referencias por kilogramo." eyebrow="Datos para el cálculo" icon={Scale} index={index} title="Ingresa tus medidas actuales" />
      <Card style={styles.profileCard}>
        <View style={styles.measurementFields}>
          <View style={styles.flex}><Field inputStyle={styles.profileInput} keyboardType="number-pad" label="Altura (cm)" labelStyle={styles.profileQuestion} onChangeText={(value) => controller.onChange?.("height", value)} placeholder="178" value={controller.values.height} /></View>
          <View style={styles.flex}><Field inputStyle={styles.profileInput} keyboardType="decimal-pad" label="Peso (kg)" labelStyle={styles.profileQuestion} onChangeText={(value) => controller.onChange?.("weight", value)} placeholder="82,5" value={controller.values.weight} /></View>
        </View>
        <Text style={textStyles.caption}>El peso inicial quedará como primera referencia de tu evolución.</Text>
      </Card>
      <JourneyFooter index={index} />
    </>
  );
}

function ActivityView({ index }: { index: number }) {
  const controller = useJourneyController();
  const activityOptions = [
    ["sedentary", "Sedentaria", "La mayor parte del día sentado"],
    ["light", "Ligera", "Caminatas y movimiento ocasional"],
    ["moderate", "Moderada", "Movimiento frecuente durante la semana"],
    ["high", "Alta", "Movimiento exigente la mayoría de los días"],
    ["very_high", "Muy alta", "Actividad física intensa o doble jornada"],
  ] as const;
  return (
    <>
      <StepHeader description="Separa el movimiento habitual de los entrenamientos para evitar contarlos dos veces." eyebrow="Datos para el cálculo" icon={Dumbbell} index={index} title="Describe tu actividad y entrenamiento" />
      <View accessibilityLabel={`Datos solicitados: ${onboardingNutritionFields.join(", ")}`}>
        <Card style={styles.profileCard}>
          <Text style={styles.profileQuestion}>Actividad habitual</Text>
          <View style={styles.activityList}>
            {activityOptions.map(([value, label, detail]) => {
              const selected = controller.values.activityLevel === value;
              return (
              <Pressable accessibilityRole="radio" accessibilityState={{ selected }} key={value} onPress={() => controller.onChange?.("activityLevel", value)} style={[styles.activityOption, selected && styles.activityOptionSelected]}>
                {selected ? <CreditSelectionBorder id="activity-selection-border" /> : null}
                <View style={styles.flex}><Text style={styles.activityLabel}>{label}</Text><Text style={styles.activityDetail}>{detail}</Text></View>
                {selected ? <SelectedActivityRadio /> : <View style={styles.radio} />}
              </Pressable>
            );})}
          </View>
          <View style={styles.trainingFrequencyField}>
            <Text style={styles.profileQuestion}>Entrenamientos por semana</Text>
            <View style={styles.trainingFrequencyChips}>
              {[[0, "0"], [1, "1"], [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6+"]].map(([value, label]) => {
                const selected = controller.values.trainingFrequency === value;
                return (
                  <Pressable accessibilityRole="radio" accessibilityState={{ selected }} key={label} onPress={() => controller.onChange?.("trainingFrequency", value)} style={[styles.trainingFrequencyChip, selected && styles.trainingFrequencyChipSelected]}>
                    {selected ? <CreditSelectionBorder id="training-frequency-border" shape="pill" /> : null}
                    <Text style={[styles.trainingFrequencyChipLabel, selected && styles.trainingFrequencyChipLabelSelected]}>{label}</Text>
                  </Pressable>
                );
              })}
            </View>
          </View>
        </Card>
      </View>
      <JourneyFooter index={index} />
    </>
  );
}

function DietaryChoiceGroup({ idPrefix, options, selectedValue, onChange }: { idPrefix: string; options: readonly (readonly [string, string])[]; selectedValue: string; onChange(value: string): void }) {
  return (
    <View style={styles.dietaryChoiceGrid}>
      {options.map(([value, label], optionIndex) => {
        const selected = value === selectedValue;
        return (
          <Pressable accessibilityRole="radio" accessibilityState={{ selected }} key={value} onPress={() => onChange(value)} style={[styles.dietaryChoiceChip, selected && styles.dietaryChoiceChipSelected]}>
            {selected ? <CreditSelectionBorder id={`${idPrefix}-${optionIndex}`} shape="pill" /> : null}
            <Text style={[styles.trainingFrequencyChipLabel, selected && styles.trainingFrequencyChipLabelSelected]}>{label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function DietaryPreferencesView({ index }: { index: number }) {
  const controller = useJourneyController();
  return (
    <>
      <StepHeader description="Cuéntanos qué alimentos podemos considerar antes de generar tu primer plan." eyebrow="Preferencias alimentarias" icon={Leaf} index={index} title="Preferencias alimentarias" />
      <Card style={[styles.profileCard, styles.dietaryCard]}>
        <View accessibilityRole="radiogroup" style={styles.dietaryQuestion}>
          <Text style={styles.profileQuestion}>Tipo de alimentación</Text>
          <DietaryChoiceGroup idPrefix="diet-type" onChange={(value) => controller.onChange?.("dietaryPattern", value)} options={[["omnivore", "Omnívora"], ["vegetarian", "Vegetariana"], ["vegan", "Vegana"], ["pescatarian", "Pescetariana"], ["flexitarian", "Flexitariana"]]} selectedValue={controller.values.dietaryPattern} />
        </View>
        <View accessibilityRole="radiogroup" style={styles.dietaryQuestion}>
          <Text style={styles.profileQuestion}>Alergias o condiciones relevantes</Text>
          <DietaryChoiceGroup idPrefix="diet-condition" onChange={(value) => controller.onChange?.("allergy", value)} options={[["", "Sin alergias"], ["gluten", "Gluten"], ["lácteos", "Lácteos"], ["frutos secos", "Frutos secos"], ["mariscos", "Mariscos"], ["otra", "Otra"]]} selectedValue={controller.values.allergy} />
          <Field
            autoCapitalize="sentences"
            label="Otra alergia o condición (opcional)"
            labelStyle={styles.profileQuestion}
            onChangeText={(value) => controller.onChange?.("allergyDetails", value)}
            placeholder="Ej. soya, huevo o condición relevante"
            value={controller.values.allergyDetails}
          />
        </View>
        <Field
          autoCapitalize="sentences"
          label="Alimentos que no consumes"
          labelStyle={styles.profileQuestion}
          onChangeText={(value) => controller.onChange?.("avoidedFoods", value)}
          placeholder="Ej. cilantro, aceitunas o champiñones"
          value={controller.values.avoidedFoods}
        />
      </Card>
      {controller.error ? <InlineNotice tone="error">{controller.error}</InlineNotice> : null}
      <JourneyFooter index={index} primary="Analizar" />
    </>
  );
}

function SummaryView({ index }: { index: number }) {
  const controller = useJourneyController();
  const estimate = controller.estimate;
  const calories = Math.round(estimate?.total_kcal ?? 1980);
  const protein = Math.round(estimate?.protein ?? 148);
  const carbs = Math.round(estimate?.carbs ?? 208);
  const fat = Math.round(estimate?.fat ?? 62);
  const allocation = (grams: number, kcalPerGram: number) => Math.round(((grams * kcalPerGram) / Math.max(calories, 1)) * 100);
  const goalLabel = ({ fat_loss: "Bajar grasa", muscle_gain: "Ganar masa muscular", maintenance: "Mantenerme", performance: "Rendimiento", healthy_eating: "Comer mejor" } as Record<string, string>)[controller.values.goal] ?? controller.values.goal;
  const activityLabel = ({ sedentary: "Sedentaria", light: "Ligera", moderate: "Moderada", high: "Alta", very_high: "Muy alta" } as Record<string, string>)[controller.values.activityLevel] ?? controller.values.activityLevel;
  return (
    <>
      <StepHeader description="Comprueba los datos y la estimación inicial antes de continuar." eyebrow="Resumen de la ficha" icon={Gauge} index={index} title="Revisa tu información" />
      <Card style={[styles.profileCard, styles.summaryCard]}>
        <Text style={styles.summarySectionEyebrow}>INFORMACIÓN PARA LA ESTIMACIÓN</Text>
        <View style={styles.summaryGrid}>
          <View style={styles.summaryCell}><Text style={styles.summaryLabel}>Objetivo</Text><Text style={styles.summaryText}>{goalLabel}</Text></View>
          <View style={styles.summaryCell}><Text style={styles.summaryLabel}>Referencia</Text><Text style={styles.summaryText}>{controller.values.weight} kg</Text></View>
          <View style={styles.summaryCell}><Text style={styles.summaryLabel}>Actividad</Text><Text style={styles.summaryText}>{activityLabel}</Text></View>
          <View style={styles.summaryCell}><Text style={styles.summaryLabel}>Entrenamiento</Text><Text style={styles.summaryText}>{controller.values.trainingFrequency >= 6 ? "6+" : controller.values.trainingFrequency} días</Text></View>
        </View>
        <Text style={styles.summarySectionEyebrow}>KCAL DE MANTENIMIENTO ESTIMADO</Text>
        <View style={styles.summaryHero}>
          <Text style={styles.summaryMetricLabel}>Calorías</Text>
          <Text style={styles.summaryValue}>{Math.round(estimate?.estimated_maintenance_kcal ?? 2340).toLocaleString("es-CL")}</Text>
          <Text style={styles.summaryMetricUnit}>kcal</Text>
        </View>
        <Text style={styles.summarySectionEyebrow}>OBJETIVO NUTRICIONAL PROPUESTO</Text>
        <NutritionKpiSection
          calories={calories}
          protein={{ allocation: allocation(protein, 4), grams: protein, perKilogram: estimate?.protein_per_kg ?? 1.8 }}
          carbs={{ allocation: allocation(carbs, 4), grams: carbs }}
          fat={{ allocation: allocation(fat, 9), grams: fat }}
        />
        <Pressable accessibilityRole="button" onPress={controller.onAdjust ?? noop} style={styles.adjustNutritionAction}>
          <Text style={styles.adjustNutritionLabel}>Ajusta objetivo nutricional</Text>
        </Pressable>
      </Card>
      {controller.error ? <InlineNotice tone="error">{controller.error}</InlineNotice> : null}
      <JourneyFooter index={index} primary="Generar primer plan" />
    </>
  );
}

const generatedDailyPlanMeals: MealPanelItem[] = [
  { id: "generated-breakfast", name: "Desayuno energético", time: "08:00", foods: [{ name: "Avena", quantity: 70, quantityUnit: "g" }, { name: "Yogur griego", quantity: 180, quantityUnit: "g" }, { name: "Arándanos", quantity: 80, quantityUnit: "g" }], calories: 515, calorieShare: 28, proteinGrams: 31, carbsGrams: 67, fatGrams: 14, proteinAllocation: 24, carbsAllocation: 52, fatAllocation: 24 },
  { id: "generated-lunch", name: "Almuerzo balanceado", time: "13:30", foods: [{ name: "Pechuga de pollo", quantity: 170, quantityUnit: "g" }, { name: "Arroz integral", quantity: 160, quantityUnit: "g" }, { name: "Ensalada mixta", quantity: 150, quantityUnit: "g" }], calories: 710, calorieShare: 39, proteinGrams: 58, carbsGrams: 76, fatGrams: 19, proteinAllocation: 33, carbsAllocation: 43, fatAllocation: 24 },
  { id: "generated-dinner", name: "Cena liviana", time: "20:00", foods: [{ name: "Salmón", quantity: 150, quantityUnit: "g" }, { name: "Papas asadas", quantity: 180, quantityUnit: "g" }, { name: "Verduras salteadas", quantity: 160, quantityUnit: "g" }], calories: 615, calorieShare: 33, proteinGrams: 41, carbsGrams: 62, fatGrams: 22, proteinAllocation: 27, carbsAllocation: 40, fatAllocation: 33 },
];

const generatedDailyPlanMealDetails: DailyPlanMealDetailItem[] = [
  {
    id: "generated-breakfast-detail",
    name: "Desayuno energético",
    time: "08:00",
    foods: [
      { id: "generated-oats", name: "Avena", quantity: 70, quantityUnit: "g", calories: 272, calorieShare: 53, proteinGrams: 9, carbsGrams: 46, fatGrams: 5, proteinAllocation: 13, carbsAllocation: 68, fatAllocation: 19 },
      { id: "generated-yogurt", name: "Yogur griego y arándanos", quantity: 260, quantityUnit: "g", calories: 243, calorieShare: 47, proteinGrams: 22, carbsGrams: 21, fatGrams: 9, proteinAllocation: 36, carbsAllocation: 35, fatAllocation: 29 },
    ],
    nutrition: { calories: 515, protein: { allocation: 24, grams: 31, perKilogram: 0.38 }, carbs: { allocation: 52, grams: 67 }, fat: { allocation: 24, grams: 14 } },
  },
  {
    id: "generated-lunch-detail",
    name: "Almuerzo balanceado",
    time: "13:30",
    foods: [
      { id: "generated-chicken", name: "Pechuga de pollo", quantity: 170, quantityUnit: "g", calories: 281, calorieShare: 40, proteinGrams: 53, carbsGrams: 0, fatGrams: 6, proteinAllocation: 76, carbsAllocation: 0, fatAllocation: 24 },
      { id: "generated-rice-salad", name: "Arroz integral y ensalada", quantity: 310, quantityUnit: "g", calories: 429, calorieShare: 60, proteinGrams: 5, carbsGrams: 76, fatGrams: 13, proteinAllocation: 5, carbsAllocation: 71, fatAllocation: 24 },
    ],
    nutrition: { calories: 710, protein: { allocation: 33, grams: 58, perKilogram: 0.7 }, carbs: { allocation: 43, grams: 76 }, fat: { allocation: 24, grams: 19 } },
  },
  {
    id: "generated-dinner-detail",
    name: "Cena liviana",
    time: "20:00",
    foods: [
      { id: "generated-salmon", name: "Salmón", quantity: 150, quantityUnit: "g", calories: 312, calorieShare: 51, proteinGrams: 33, carbsGrams: 0, fatGrams: 20, proteinAllocation: 42, carbsAllocation: 0, fatAllocation: 58 },
      { id: "generated-potatoes-vegetables", name: "Papas y verduras", quantity: 340, quantityUnit: "g", calories: 303, calorieShare: 49, proteinGrams: 8, carbsGrams: 62, fatGrams: 2, proteinAllocation: 11, carbsAllocation: 82, fatAllocation: 7 },
    ],
    nutrition: { calories: 615, protein: { allocation: 27, grams: 41, perKilogram: 0.5 }, carbs: { allocation: 40, grams: 62 }, fat: { allocation: 33, grams: 22 } },
  },
];

function GeneratedDailyPlanView() {
  const controller = useJourneyController();
  if (controller.proposal?.dailyplan) {
    return (
      <>
        <StepHeader description="Revisa el plan generado antes de guardarlo en tu biblioteca." eyebrow="Plan del día" icon={BookOpen} index={13} title="Tu primer plan diario" />
        <ProposalDailyPlanCard dailyplan={controller.proposal.dailyplan} />
        {controller.error ? <InlineNotice tone="error">{controller.error}</InlineNotice> : null}
        <CreditContinueButton />
      </>
    );
  }
  return (
    <>
      <EntityDetailPage
        entity="dailyPlan"
        eyebrow="PLAN DEL DÍA"
        indicators={[{ icon: "meal", label: "comidas", value: 3 }, { icon: "food", label: "alimentos", value: 9 }]}
        nutrition={{
          calories: 1840,
          protein: { allocation: 28, grams: 130, perKilogram: 1.6 },
          carbs: { allocation: 45, grams: 205 },
          fat: { allocation: 27, grams: 55 },
        }}
        title="Plan equilibrado · Día 1">
        <EntityDetailSection title="Tabla de comparación entre comidas">
          <MealPanels items={generatedDailyPlanMeals} showEditTab={false} />
        </EntityDetailSection>
        <EntityDetailSection title="Detalle de cada Comida">
          <DailyPlanMealDetailList items={generatedDailyPlanMealDetails} />
        </EntityDetailSection>
      </EntityDetailPage>
      <CreditContinueButton />
    </>
  );
}

const plans = [
  { accent: tokens.color.fat, caption: "Incluido sin costo.", name: "Free", price: "$0/mes" },
  { accent: tokens.color.carbs, annualPrice: "$39.900/año · Ahorra 17%", name: "Basic", price: "$3.990/mes" },
  { accent: tokens.color.protein, annualPrice: "$69.900/año · Ahorra 17%", name: "Pro", price: "$6.990/mes" },
] as const;

function PlansView({ index }: { index: number }) {
  const controller = useJourneyController();
  return (
    <>
      <StepHeader brandedCentered description="Compara lo que incluyen Free, Basic y Pro. Puedes cambiar de plan más adelante." eyebrow="Planes disponibles" icon={BookOpen} index={index} title="Elige un plan" />
      <View style={styles.planList}>
        {plans.map((plan) => (
          <SubscriptionPlanCard accent={plan.accent} benefits={commercialPlanBenefits[plan.name]} caption={"caption" in plan ? plan.caption : undefined} key={plan.name} name={plan.name} price={plan.price}>
            {plan.name === "Free" ? <SubscriptionPurchaseButton label="Continuar con Free" onPress={() => controller.onChoosePlan?.("Free")} /> : (
              <View style={styles.subscriptionActions}>
                <SubscriptionPurchaseButton label={`Mensual · ${plan.price}`} onPress={() => controller.onChoosePlan?.(plan.name)} />
                <SubscriptionPurchaseButton label={`Anual · ${plan.annualPrice}`} onPress={() => controller.onChoosePlan?.(plan.name)} />
              </View>
            )}
          </SubscriptionPlanCard>
        ))}
      </View>
      {controller.error ? <InlineNotice tone="error">{controller.error}</InlineNotice> : null}
      <Text style={styles.quietCenter}>Precios mensuales en CLP. También habrá opciones anuales.</Text>
    </>
  );
}

const views: Record<OnboardingJourneyStep, (props: { index: number }) => ReactNode> = {
  login: LoginView,
  value: ValueView,
  structure: StructureView,
  panels: PanelsView,
  control: ControlView,
  progress: ProgressView,
  disclosures: DisclosuresView,
  goal: GoalView,
  identity: IdentityView,
  measurements: MeasurementsView,
  activity: ActivityView,
  dietary: DietaryPreferencesView,
  summary: SummaryView,
  dailyPlan: GeneratedDailyPlanView,
  plans: PlansView,
};

export function OnboardingJourneyView({ controller, step }: { controller?: OnboardingJourneyController; step: OnboardingJourneyStep }) {
  const index = onboardingJourneySteps.findIndex((item) => item.key === step);
  const ViewComponent = views[step];
  const resolvedController = useMemo(() => controller ?? { values: galleryValues }, [controller]);
  const swipeResponder = useMemo(() => PanResponder.create({
    onMoveShouldSetPanResponder: (_event, gesture) => Boolean(controller) && index >= 1 && index <= 5 && Math.abs(gesture.dx) > 18 && Math.abs(gesture.dx) > Math.abs(gesture.dy),
    onPanResponderRelease: (_event, gesture) => {
      if (gesture.dx <= -48) resolvedController.onNext?.();
      if (gesture.dx >= 48) resolvedController.onBack?.();
    },
  }), [controller, index, resolvedController]);
  return (
    <JourneyControllerContext.Provider value={resolvedController}>
      <View {...swipeResponder.panHandlers} style={[styles.screen, index >= 7 && index <= 12 && styles.profileScreen]}><ViewComponent index={index} /></View>
    </JourneyControllerContext.Provider>
  );
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, gap: tokens.spacing.lg, minHeight: 690, paddingBottom: tokens.spacing.xl, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg + (tokens.spacing.md * 2) + 18 },
  profileScreen: { paddingTop: tokens.spacing.lg + (tokens.spacing.md * 2) + 18 - 32 },
  intro: { alignItems: "flex-start", gap: tokens.spacing.sm },
  introCentered: { alignItems: "center" },
  centeredLogo: { alignItems: "center", justifyContent: "center", width: "100%" },
  centeredText: { textAlign: "center" },
  centeredTitleSpacing: { marginBottom: tokens.spacing.sm, marginTop: tokens.spacing.xxl + tokens.spacing.md },
  stepMeta: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, width: "100%" },
  stepCount: { color: tokens.color.textSoft, fontSize: 10, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, letterSpacing: 1 },
  progressTrack: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, flex: 1, height: 3, overflow: "hidden" },
  progressFill: { backgroundColor: tokens.color.interactivePrimary, height: "100%" },
  iconWell: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, height: 54, justifyContent: "center", marginTop: tokens.spacing.sm, width: 54 },
  eyebrow: { color: tokens.color.interactivePrimary, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.2, textTransform: "uppercase" },
  disclosuresEyebrow: { color: tokens.color.textMuted },
  title: { color: tokens.color.textMain, fontSize: 28, fontWeight: tokens.weight.extraBold, letterSpacing: -0.8, lineHeight: 32 },
  description: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  footer: { gap: tokens.spacing.sm, marginTop: "auto" },
  explanationFooter: { alignItems: "center", gap: tokens.spacing.md, marginBottom: 48, marginTop: "auto" },
  explanationFooterWithAction: { gap: tokens.spacing.xs, marginBottom: 34 },
  explanationDots: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "center", minHeight: 40 },
  explanationDot: { backgroundColor: tokens.color.borderStrong, borderRadius: 5, height: 10, overflow: "hidden", width: 10 },
  explanationDotActive: { backgroundColor: "transparent", transform: [{ scale: 1.25 }] },
  continueChip: { alignItems: "center", borderRadius: tokens.radius.pill, justifyContent: "center", minHeight: 34, overflow: "hidden", paddingHorizontal: tokens.spacing.lg },
  continueChipInset: { backgroundColor: tokens.color.surfaceApp, borderRadius: tokens.radius.pill, bottom: 2, left: 2, position: "absolute", right: 2, top: 2 },
  continueChipText: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  creditContinueButton: { alignItems: "center", borderRadius: tokens.radius.lg, justifyContent: "center", minHeight: 48, overflow: "hidden" },
  creditContinueButtonChip: { borderRadius: tokens.radius.pill, minHeight: 34, paddingHorizontal: tokens.spacing.lg },
  creditContinueLabel: { color: tokens.color.surfaceApp, fontSize: tokens.type.body, fontWeight: tokens.weight.extraBold },
  creditContinueLabelChip: { fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  actionDisabled: { opacity: 0.55 },
  profileProgress: { alignItems: "center", flexDirection: "row", justifyContent: "center", paddingHorizontal: tokens.spacing.xl, width: "100%" },
  profileProgressGroup: { alignItems: "center", gap: tokens.spacing.sm, width: "100%" },
  profileProgressEyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.regular, letterSpacing: 1.2, textAlign: "center", textTransform: "uppercase" },
  profileProgressEyebrowTextMain: { color: tokens.color.textMain },
  profileProgressItem: { alignItems: "center", flex: 1, flexDirection: "row" },
  profileProgressItemLast: { flex: 0 },
  profileProgressLine: { backgroundColor: tokens.color.borderStrong, flex: 1, height: 2 },
  profileProgressDot: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderStrong, borderRadius: 7, borderWidth: 1, height: 14, overflow: "hidden", width: 14 },
  backAction: { alignItems: "center", alignSelf: "center", flexDirection: "row", gap: tokens.spacing.xs, minHeight: 40, paddingHorizontal: tokens.spacing.md },
  profileFooter: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  profileBackAction: { alignSelf: "auto", paddingLeft: 0 },
  profilePrimaryAction: { minWidth: 144 },
  backLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  explanationCard: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.md, padding: tokens.spacing.md },
  explanationIcon: { alignItems: "center", backgroundColor: tokens.color.surfaceElevated, borderRadius: tokens.radius.md, height: 36, justifyContent: "center", width: 36 },
  explanationCopy: { flex: 1, gap: 2 },
  explanationTitle: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  explanationBody: { color: tokens.color.textMuted, fontSize: 12, lineHeight: 17 },
  valueFeatures: { gap: tokens.spacing.sm },
  loginHero: { alignItems: "center", gap: tokens.spacing.md, marginTop: 64 },
  loginAction: { marginBottom: 114, marginTop: "auto" },
  loginKicker: { color: tokens.color.program, fontSize: 11, fontWeight: tokens.weight.extraBold, letterSpacing: 1.5 },
  loginTitle: { color: tokens.color.textMain, fontSize: 32, fontWeight: tokens.weight.extraBold, letterSpacing: -1, lineHeight: 37, marginBottom: tokens.spacing.sm, textAlign: "center" },
  cardTitle: { color: tokens.color.textMain, fontSize: 19, fontWeight: tokens.weight.bold },
  quietCenter: { color: tokens.color.textSoft, fontSize: 11, lineHeight: 16, textAlign: "center" },
  levels: { gap: tokens.spacing.sm },
  levelRow: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.md, padding: tokens.spacing.md },
  levelMarker: { alignItems: "center", borderRadius: tokens.radius.md, height: 34, justifyContent: "center", width: 34 },
  levelNumber: { color: tokens.color.surfaceApp, fontSize: tokens.type.caption, fontWeight: tokens.weight.extraBold },
  levelCopy: { flex: 1, gap: 2 },
  levelTitle: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  levelDetail: { color: tokens.color.textMuted, fontSize: 11 },
  panelEntityHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  panelEyebrow: { color: tokens.color.dailyPlan, fontSize: 10, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1 },
  panelEntityTitle: { color: tokens.color.textMain, fontSize: 18, fontWeight: tokens.weight.bold, marginTop: 3 },
  panelPreview: { gap: tokens.spacing.xs, padding: tokens.spacing.md },
  panelPreviewValue: { color: tokens.color.textMain, fontSize: 24, fontWeight: tokens.weight.extraBold },
  panelPreviewLabel: { color: tokens.color.textMuted, fontSize: 12 },
  panelBars: { flexDirection: "row", gap: 2, height: 8, marginTop: tokens.spacing.sm, overflow: "hidden" },
  panelBar: { borderRadius: tokens.radius.pill },
  panelHint: { color: tokens.color.textSoft, fontSize: 11, textAlign: "center" },
  controlFlow: { gap: tokens.spacing.sm },
  metricRow: { alignItems: "baseline", flexDirection: "row", justifyContent: "space-between" },
  metricLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  metricValue: { color: tokens.color.textMain, fontSize: 28, fontWeight: tokens.weight.extraBold },
  metricTrack: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, height: 10, overflow: "hidden" },
  metricFill: { backgroundColor: tokens.color.success, borderRadius: tokens.radius.pill, height: "100%", width: "86%" },
  progressFacts: { gap: tokens.spacing.sm, marginTop: tokens.spacing.sm },
  noticeStack: { gap: tokens.spacing.sm },
  optionGrid: { gap: tokens.spacing.sm },
  optionCard: { alignItems: "center", backgroundColor: "transparent", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.lg, borderWidth: 1, flexDirection: "row", justifyContent: "space-between", minHeight: 50, paddingHorizontal: tokens.spacing.lg },
  optionCardSelected: { backgroundColor: tokens.color.surfaceElevated, borderColor: "transparent", borderWidth: 0, overflow: "hidden" },
  optionText: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  optionTextSelected: { color: tokens.color.textMain },
  goalSelectionCheck: { height: 22, width: 22 },
  measurementFields: { gap: tokens.spacing.md },
  profileCard: { backgroundColor: "transparent" },
  summaryCard: { marginTop: -tokens.spacing.md },
  profileInput: { paddingVertical: 0, textAlign: "center", textAlignVertical: "center" },
  identityChoiceField: { gap: 7 },
  identityChoiceRow: { flexDirection: "row", gap: tokens.spacing.sm },
  identityChoiceSelected: { backgroundColor: tokens.color.surfaceElevated, borderColor: "transparent", borderWidth: 0, overflow: "hidden" },
  flex: { flex: 1 },
  fieldLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  profileQuestion: { color: tokens.color.textMain, fontSize: tokens.type.label, fontWeight: tokens.weight.regular, letterSpacing: 1.1, textTransform: "uppercase" },
  activityList: { gap: tokens.spacing.sm },
  activityOption: { alignItems: "center", borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.md, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.md, padding: tokens.spacing.md },
  activityOptionSelected: { backgroundColor: tokens.color.surfaceElevated, borderColor: "transparent", borderWidth: 0, overflow: "hidden" },
  activityLabel: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  activityDetail: { color: tokens.color.textMuted, fontSize: 11, marginTop: 2 },
  radio: { alignItems: "center", borderColor: tokens.color.borderStrong, borderRadius: 10, borderWidth: 1, height: 20, justifyContent: "center", width: 20 },
  radioSelected: { borderWidth: 0, overflow: "hidden" },
  trainingFrequencyField: { gap: 7 },
  trainingFrequencyChips: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  trainingFrequencyChip: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, flex: 1, justifyContent: "center", minHeight: 34, minWidth: 0, paddingHorizontal: tokens.spacing.sm },
  trainingFrequencyChipSelected: { backgroundColor: tokens.color.surfaceElevated, borderColor: "transparent", borderWidth: 0, overflow: "hidden" },
  trainingFrequencyChipLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  trainingFrequencyChipLabelSelected: { color: tokens.color.textMain },
  dietaryQuestion: { gap: 7 },
  dietaryCard: { gap: tokens.spacing.xl },
  dietaryChoiceGrid: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  dietaryChoiceChip: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, flexBasis: "30%", flexGrow: 1, justifyContent: "center", minHeight: 34, minWidth: 0, paddingHorizontal: tokens.spacing.sm },
  dietaryChoiceChipSelected: { backgroundColor: tokens.color.surfaceElevated, borderColor: "transparent", borderWidth: 0, overflow: "hidden" },
  summaryHero: { alignItems: "center", backgroundColor: tokens.color.kcalSurface, borderColor: tokens.color.kcalBorder, borderRadius: tokens.component.nutritionKpi.regular.totalRadius, borderWidth: tokens.component.nutritionKpi.regular.totalBorderWidth, gap: 1, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.sm },
  summaryValue: { color: tokens.color.textMain, fontSize: 34, fontWeight: tokens.weight.extraBold, letterSpacing: -1 },
  summaryGrid: { alignSelf: "stretch", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  summaryCell: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, flexBasis: "45%", flexGrow: 1, gap: 3, minWidth: 0, padding: tokens.spacing.sm },
  summaryLabel: { color: tokens.color.textSoft, fontSize: 10, textTransform: "uppercase" },
  summaryText: { color: tokens.color.textMain, fontSize: 12, fontWeight: tokens.weight.bold },
  summarySectionEyebrow: { alignSelf: "stretch", color: tokens.color.textMain, fontSize: tokens.type.label, fontWeight: tokens.weight.regular, letterSpacing: 1.1, marginTop: tokens.spacing.sm, textAlign: "left", textTransform: "uppercase" },
  summaryMetricLabel: { color: tokens.color.textMuted, fontSize: 12, fontWeight: tokens.weight.medium },
  summaryMetricUnit: { color: tokens.color.textSoft, fontSize: 11, fontWeight: tokens.weight.medium },
  adjustNutritionAction: { alignItems: "center", justifyContent: "center", minHeight: 40, paddingHorizontal: tokens.spacing.md },
  adjustNutritionLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium },
  planList: { gap: tokens.spacing.sm },
  subscriptionActions: { gap: tokens.spacing.sm },
});
