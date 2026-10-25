import {
  Apple,
  Beef,
  BookOpen,
  CalendarDays,
  Carrot,
  ChevronLeft,
  CircleUserRound,
  ClipboardList,
  Dumbbell,
  Eye,
  Fish,
  Gauge,
  HeartPulse,
  Leaf,
  LibraryBig,
  LockKeyhole,
  Pin,
  Scale,
  Sparkles,
  Target,
  Utensils,
} from "lucide-react-native";
import { createContext, type ComponentType, type ReactNode, useCallback, useContext, useLayoutEffect, useMemo, useState } from "react";
import { Animated, Image, PanResponder, type PanResponderGestureState, Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View, type LayoutChangeEvent, type StyleProp, type TextStyle, type ViewStyle } from "react-native";
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from "react-native-svg";

import { DailyPlanMealDetailList, type DailyPlanMealDetailItem, EntityDetailPage, EntityDetailSection } from "@/components/details";
import { commitmentKinds, commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { ResponsibleUseConfirmationNotice, ResponsibleUsePolicyLink } from "@/components/disclosures/responsible-use-content";
import { KpiAllocationBar, NutritionKpiSection, ProteinPerKilogramBadge } from "@/components/nutrition";
import { MealPanels, type MealPanelItem } from "@/components/panels";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { ProposalDailyPlanCard } from "@/components/proposals/proposal-preview";
import { commercialPlanBenefits, SubscriptionPlanCard, SubscriptionPurchaseButton } from "@/components/subscriptions/subscription-plan-card";
import { AssistantGradientIcon, Button, Card, EntityIcon, Field, InlineNotice, MyScoopeBrandLogo, NativeDateTimeField, NativeMeasurementField, textStyles, type EntityKind } from "@/components/ui";
import type { OnboardingEstimate, ProposalDetail } from "@/api/types";
import { tokens } from "@/design/tokens";
import { localDateValue } from "@/presentation/date-time-values";

export const onboardingJourneySteps = [
  { key: "login", shortLabel: "Acceso", label: "Acceso" },
  { key: "value", shortLabel: "Funciones", label: "Funciones principales" },
  { key: "structure", shortLabel: "Estructura", label: "Organización nutricional" },
  { key: "control", shortLabel: "Asistencia", label: "Asistencia y decisiones" },
  { key: "panels", shortLabel: "Paneles", label: "Lectura de paneles" },
  { key: "panelsCopy", shortLabel: "Paneles", label: "Lectura de paneles" },
  { key: "progress", shortLabel: "Progreso", label: "Seguimiento del progreso" },
  { key: "disclosures", shortLabel: "Límites", label: "Información y límites" },
  { key: "goal", shortLabel: "Objetivo", label: "Objetivo nutricional" },
  { key: "identity", shortLabel: "Datos", label: "Datos personales" },
  { key: "measurements", shortLabel: "Medidas", label: "Medidas corporales" },
  { key: "activity", shortLabel: "Actividad", label: "Actividad y entrenamiento" },
  { key: "dietary", shortLabel: "Preferencias", label: "Preferencias alimentarias" },
  { key: "summary", shortLabel: "Resumen", label: "Resumen de la ficha" },
  { key: "dailyPlan", shortLabel: "Minuta", label: "Primera minuta diaria" },
  { key: "plans", shortLabel: "Planes", label: "Planes disponibles" },
] as const;

export type OnboardingJourneyStep = (typeof onboardingJourneySteps)[number]["key"];

const onboardingStoryboardTopInsetReduction = 20;
const earlyOnboardingStoryboardTopInsetReduction = onboardingStoryboardTopInsetReduction + 18;

export function topInsetReductionForOnboardingStoryboard(step: OnboardingJourneyStep) {
  return onboardingJourneySteps.findIndex((item) => item.key === step) < 7
    ? earlyOnboardingStoryboardTopInsetReduction
    : onboardingStoryboardTopInsetReduction;
}

export function presentationPropsForOnboardingStep(step: OnboardingJourneyStep) {
  const index = onboardingJourneySteps.findIndex((item) => item.key === step);
  const usesRefinedPresentation = index >= 1;
  return {
    conciseSexEyebrow: usesRefinedPresentation,
    contentSizedDietaryChips: usesRefinedPresentation,
    disclosuresTitleSpacingReduction: index === 7 ? 18 : 0,
    fixedDisclosuresFooter: index === 7,
    fixedLoginActionBottomSpacing: 0,
    fixedProfileChrome: index >= 8 && index <= 13,
    fixedProfileFooterBottomSpacing: index >= 8 && index <= 13 ? 46 : 0,
    fullWidthExplanationTransition: index >= 1 && index <= 6,
    hideCalculationReviewDisclosure: usesRefinedPresentation,
    progressiveAllergyDetails: usesRefinedPresentation,
    profileEyebrowsMuted: usesRefinedPresentation,
    profileProgressBottomSpacing: index >= 8 && index <= 13 ? 24 : 0,
    profileProgressEyebrowBottomSpacing: index >= 8 && index <= 13 ? 18 : 0,
    profileQuestionSpacing: index >= 8 && index <= 13 ? 24 : 0,
    profileProgressWidthReduction: index >= 8 && index <= 13 ? 36 : 0,
    profileTitleBottomSpacingReduction: index >= 8 && index <= 13 ? 12 : 0,
    showGoalOptionsEyebrow: usesRefinedPresentation,
    showProfileControlBleed: usesRefinedPresentation,
    storyboardSummaryLayout: usesRefinedPresentation,
    topInsetReduction: usesRefinedPresentation
      ? topInsetReductionForOnboardingStoryboard(step)
        + (index >= 1 && index <= 7 ? 20 : 0)
        + (index >= 7 ? 20 : 0)
        + (step === "plans" ? 20 : 0)
      : 0,
  };
}

const explanationSteps = onboardingJourneySteps.slice(1, 7);
const mealFoodIcons = [Apple, Carrot, Beef, Fish];

export const onboardingNutritionFields = ["goal", "birth_date", "sex", "height_cm", "weight_kg", "activity_level", "training_frequency", "dietary_pattern", "allergies_or_intolerances", "avoided_foods"] as const;

type Icon = ComponentType<{ color?: string; size?: number; strokeWidth?: number }>;

const noop = () => undefined;
const loginBackgroundSource = require("../../../assets/images/login-background.jpg");

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
  loginDisabled?: boolean;
  loginLabel?: string;
  onChange?(field: keyof OnboardingJourneyValues, value: string | number): void;
  onNext?(): void;
  onBack?(): void;
  onLogin?(): void;
  onAdjust?(): void;
  onChoosePlan?(plan: "Free" | "Basic" | "Pro"): void;
};

export const onboardingJourneyPreviewValues: OnboardingJourneyValues = {
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

const JourneyControllerContext = createContext<OnboardingJourneyController>({ values: onboardingJourneyPreviewValues });
const JourneyPresentationContext = createContext({
  conciseSexEyebrow: false,
  contentSizedDietaryChips: false,
  disclosuresTitleSpacingReduction: 0,
  externalExplanationChrome: false,
  fixedDisclosuresFooter: false,
  fixedLoginActionBottomSpacing: 0,
  fixedProfileChrome: false,
  fixedProfileFooterBottomSpacing: 0,
  hideCalculationReviewDisclosure: false,
  progressiveAllergyDetails: false,
  profileEyebrowsMuted: false,
  profileProgressEyebrowBottomSpacing: 0,
  profileProgressBottomSpacing: 0,
  profileQuestionSpacing: 0,
  profileProgressWidthReduction: 0,
  profileTitleBottomSpacingReduction: 0,
  showGoalOptionsEyebrow: false,
  showProfileControlBleed: false,
  storyboardSummaryLayout: false,
});

function useJourneyController() {
  return useContext(JourneyControllerContext);
}

function useProfileQuestionStyle() {
  const { profileEyebrowsMuted } = useContext(JourneyPresentationContext);
  return [styles.profileQuestion, profileEyebrowsMuted && styles.profileQuestionMuted];
}

function StepHeader({ brandedCentered = false, icon: IconComponent, index, eyebrow, showIconAboveTitle = false, showProgress = true, title, titleAccessory, titleStyle, titleTopSpacingReduction = 0, description, descriptionSecondary, descriptionAccessory }: {
  brandedCentered?: boolean;
  description: ReactNode;
  descriptionSecondary?: ReactNode;
  descriptionAccessory?: ReactNode;
  eyebrow: string;
  icon: Icon;
  index: number;
  showIconAboveTitle?: boolean;
  showProgress?: boolean;
  title: string;
  titleAccessory?: ReactNode;
  titleStyle?: StyleProp<TextStyle>;
  titleTopSpacingReduction?: number;
}) {
  const { disclosuresTitleSpacingReduction, externalExplanationChrome, fixedProfileChrome, profileTitleBottomSpacingReduction } = useContext(JourneyPresentationContext);
  const isExplanation = index >= 1 && index <= 6;
  const isProfileStep = index >= 8 && index <= 13;
  const usesBrandedHeader = isExplanation || brandedCentered;
  const isCenteredIntro = index <= 13 || brandedCentered;
  const usesCenteredTitleSpacing = (index <= 7 || brandedCentered) && !externalExplanationChrome;
  return (
    <View style={[styles.intro, isCenteredIntro && styles.introCentered, isProfileStep && fixedProfileChrome && profileTitleBottomSpacingReduction > 0 && { marginBottom: -profileTitleBottomSpacingReduction }]}>
      {usesBrandedHeader ? (!externalExplanationChrome ? <View style={[styles.centeredLogo, index === 7 && styles.disclosuresLogo]}><MyScoopeBrandLogo scale={isExplanation ? 1.1 : index === 7 ? 0.88 : 1} /></View> : null) : isProfileStep ? (!fixedProfileChrome ? <ProfileProgress index={index} /> : null) : index === 7 || !showProgress ? null : (
        <View style={styles.stepMeta}>
          <Text style={styles.stepCount}>{String(index + 1).padStart(2, "0")} / {onboardingJourneySteps.length}</Text>
          <View accessibilityLabel={`Paso ${index + 1} de ${onboardingJourneySteps.length}`} style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${((index + 1) / onboardingJourneySteps.length) * 100}%` }]} />
          </View>
        </View>
      )}
      {!usesBrandedHeader || showIconAboveTitle ? <View style={styles.iconWell}><IconComponent color={tokens.color.entityIconForeground} size={27} strokeWidth={1.8} /></View> : null}
      {!usesBrandedHeader && !isProfileStep && eyebrow ? <Text style={[styles.eyebrow, isCenteredIntro && styles.centeredText, index === 7 && styles.disclosuresEyebrow]}>{eyebrow}</Text> : null}
      <Text style={[
        styles.title,
        isCenteredIntro && styles.centeredText,
        usesCenteredTitleSpacing && !showIconAboveTitle && styles.centeredTitleSpacing,
        titleTopSpacingReduction > 0 && { marginTop: -titleTopSpacingReduction },
        isExplanation && { marginBottom: (usesCenteredTitleSpacing ? tokens.spacing.sm : 0) + 10 },
        index === 7 && disclosuresTitleSpacingReduction > 0 && { marginTop: styles.centeredTitleSpacing.marginTop - disclosuresTitleSpacingReduction },
        titleStyle,
      ]}>{title}</Text>
      {titleAccessory}
      {!isProfileStep && description ? <Text style={[styles.description, isExplanation && styles.explanationDescription, isCenteredIntro && styles.centeredText, index === 1 && styles.valueDescription, index === 7 && styles.disclosuresDescription]}>{description}</Text> : null}
      {descriptionSecondary ? <Text style={[styles.description, styles.explanationDescription, styles.centeredText, styles.valueDescription, styles.valueSecondaryDescription]}>{descriptionSecondary}</Text> : null}
      {descriptionAccessory}
    </View>
  );
}

function ExplanationDots({ action, compact = false, forceVisible = false, index }: { action?: ReactNode; compact?: boolean; forceVisible?: boolean; index: number }) {
  const { externalExplanationChrome } = useContext(JourneyPresentationContext);
  if (externalExplanationChrome && !forceVisible) return null;
  const activeIndex = index - 1;
  return (
    <View style={[styles.explanationFooter, compact && styles.explanationFooterCompact, action ? styles.explanationFooterWithAction : null]}>
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
      {action ? <View style={styles.explanationFooterAction}>{action}</View> : null}
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

function CreditSelectionBorder({ id, shape = "md" }: { id: string; shape?: "md" | "lg" | "pill" | "identity" }) {
  const radius = shape === "identity" ? 22 : shape === "pill" ? 17 : shape === "lg" ? tokens.radius.lg : tokens.radius.md;
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
  const { profileEyebrowsMuted, profileProgressBottomSpacing, profileProgressEyebrowBottomSpacing, profileProgressWidthReduction } = useContext(JourneyPresentationContext);
  const activeIndex = index - 7;
  return (
    <View style={[styles.profileProgressGroup, profileProgressBottomSpacing > 0 && { marginBottom: profileProgressBottomSpacing }]}>
      <Text style={[styles.profileProgressEyebrow, index >= 9 && styles.profileProgressEyebrowTextMain, profileEyebrowsMuted && styles.profileQuestionMuted, profileProgressEyebrowBottomSpacing > 0 && { marginBottom: profileProgressEyebrowBottomSpacing }]}>OBJETIVO Y PLANIFICACIÓN</Text>
      <View
        accessibilityLabel={`Paso ${activeIndex + 1} de 6 de tu perfil`}
        style={[styles.profileProgress, profileProgressWidthReduction > 0 && { paddingHorizontal: tokens.spacing.xl + (profileProgressWidthReduction / 2) }]}
      >
        {Array.from({ length: 6 }, (_, stepIndex) => (
          <View key={stepIndex} style={[styles.profileProgressItem, stepIndex === 5 && styles.profileProgressItemLast]}>
            <View style={[styles.profileProgressDot, stepIndex <= activeIndex && styles.profileProgressDotActive]} />
            {stepIndex < 5 ? (
              <View style={[styles.profileProgressLine, stepIndex < activeIndex && styles.profileProgressLineActive]} />
            ) : null}
          </View>
        ))}
      </View>
    </View>
  );
}

function ProfileStepLayout({ children, index, primary }: { children: ReactNode; index: number; primary?: string }) {
  const { fixedProfileChrome, fixedProfileFooterBottomSpacing } = useContext(JourneyPresentationContext);
  const [contentHeight, setContentHeight] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(0);
  const contentOverflows = contentHeight > viewportHeight + 1;
  if (!fixedProfileChrome) {
    return <>{children}<JourneyFooter index={index} primary={primary} /></>;
  }
  return (
    <View style={styles.fixedProfileLayout}>
      <ProfileProgress index={index} />
      <ScrollView
        alwaysBounceVertical={contentOverflows}
        bounces={contentOverflows}
        contentContainerStyle={styles.fixedProfileScrollContent}
        keyboardShouldPersistTaps="handled"
        onContentSizeChange={(_width, height) => setContentHeight(height)}
        onLayout={({ nativeEvent }) => setViewportHeight(nativeEvent.layout.height)}
        scrollEnabled={contentOverflows}
        showsVerticalScrollIndicator={false}
        style={styles.fixedProfileScroll}
      >
        {children}
      </ScrollView>
      <View style={fixedProfileFooterBottomSpacing > 0 ? { marginBottom: fixedProfileFooterBottomSpacing } : undefined}>
        <JourneyFooter index={index} primary={primary} />
      </View>
    </View>
  );
}

function DisclosuresStepLayout({ children, index }: { children: ReactNode; index: number }) {
  const { fixedDisclosuresFooter, fixedProfileFooterBottomSpacing } = useContext(JourneyPresentationContext);
  const [contentHeight, setContentHeight] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(0);
  const contentOverflows = contentHeight > viewportHeight + 1;
  if (!fixedDisclosuresFooter) {
    return <>{children}<JourneyFooter index={index} primary="Entiendo y quiero continuar" /></>;
  }
  return (
    <View style={styles.fixedProfileLayout}>
      <ScrollView
        alwaysBounceVertical={contentOverflows}
        bounces={contentOverflows}
        contentContainerStyle={styles.fixedProfileScrollContent}
        onContentSizeChange={(_width, height) => setContentHeight(height)}
        onLayout={({ nativeEvent }) => setViewportHeight(nativeEvent.layout.height)}
        scrollEnabled={contentOverflows}
        showsVerticalScrollIndicator={false}
        style={[styles.fixedProfileScroll, styles.disclosuresScroll]}
      >
        {children}
      </ScrollView>
      <View style={fixedProfileFooterBottomSpacing > 0 ? { marginBottom: fixedProfileFooterBottomSpacing } : undefined}>
        <JourneyFooter index={index} primary="Entiendo y quiero continuar" />
      </View>
    </View>
  );
}

function JourneyFooter({ index, primary = "Continuar", secondary = "Atrás" }: { index: number; primary?: string; secondary?: string }) {
  const controller = useJourneyController();
  if (index >= 8 && index <= 13) {
    return (
      <View style={[styles.footer, styles.profileFooter]}>
        <Pressable accessibilityRole="button" disabled={controller.busy} onPress={controller.onBack ?? noop} style={[styles.backAction, styles.profileBackAction]}>
          <ChevronLeft color={tokens.color.textMuted} size={16} />
          <Text style={styles.backLabel}>{secondary}</Text>
        </Pressable>
        <View style={styles.profilePrimaryAction}>
          {index === 13 ? <CreditContinueButton chip label={primary} /> : <ContinueChip label={primary} />}
        </View>
      </View>
    );
  }
  return (
    <View style={styles.footer}>
      {index === 7 ? <CreditContinueButton label={primary} /> : <Button label={primary} loading={controller.busy} onPress={controller.onNext ?? noop} />}
      {index === 7 ? <View style={styles.disclosuresConfirmationSpacing}><ResponsibleUseConfirmationNotice /></View> : null}
      {index > 0 ? (
        <Pressable accessibilityRole="button" disabled={controller.busy} onPress={controller.onBack ?? noop} style={[styles.backAction, index === 7 && styles.disclosuresBackAction]}>
          {index === 7 ? null : <ChevronLeft color={tokens.color.textMuted} size={16} />}
          <Text style={styles.backLabel}>{index === 7 ? "Volver" : secondary}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

function ExplanationCard({ body, children, icon: IconComponent, style, title }: { body: string; children?: ReactNode; icon: Icon; style?: StyleProp<ViewStyle>; title: string }) {
  return (
    <View style={[styles.explanationCard, style]}>
      <View style={styles.explanationCardRow}>
        <View style={styles.explanationCopy}>
          <Text style={styles.explanationTitle}>{title}</Text>
          <Text style={styles.explanationBody}>{body}</Text>
        </View>
        <View style={styles.explanationIcon}><IconComponent color={tokens.color.entityIconForeground} size={18} /></View>
      </View>
      {children}
    </View>
  );
}

function TopAccentCard({ accent, children, style }: { accent: string; children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return (
    <View style={[styles.levelRowFrame, { backgroundColor: accent }]}>
      <View style={[styles.levelRow, style]}>{children}</View>
    </View>
  );
}

function LoginView({ index }: { index: number }) {
  const controller = useJourneyController();
  const { height: viewportHeight } = useWindowDimensions();
  const loginImageHeight = Math.max(280, Math.min(396, viewportHeight - 416));
  return (
    <View style={styles.loginContent}>
      <View style={[styles.centeredLogo, styles.loginLogo]}>
        <MyScoopeBrandLogo />
      </View>
      <View style={[styles.loginImageStage, { height: loginImageHeight }]}>
        <Image accessibilityIgnoresInvertColors resizeMode="contain" source={loginBackgroundSource} style={[styles.loginBackgroundImage, { height: loginImageHeight }]} />
      </View>
      <View accessibilityLabel={`Paso ${index + 1} de ${onboardingJourneySteps.length}`} style={styles.loginHero}>
        <View accessibilityLabel="Consigue tu Prime Físico" accessible style={styles.loginTitleRow}>
          <Text style={styles.loginTitle}>Consigue tu</Text>
          <View style={styles.loginTitleChip}>
            <Text style={styles.loginTitleChipText}>Prime</Text>
          </View>
          <Text style={styles.loginTitle}>Físico</Text>
        </View>
        <Text style={[textStyles.muted, styles.centeredText, styles.loginDescription]}>Planifica, Ejecuta y Aprende sobre alimentación para ver resultados importantes</Text>
        <View style={styles.loginAction}>
          {controller.error ? <InlineNotice tone="error">{controller.error}</InlineNotice> : null}
          <Button disabled={controller.loginDisabled} label={controller.loginLabel ?? "Iniciar sesión o crear cuenta"} loading={controller.busy} multicolorSurface="app" onPress={controller.onLogin ?? noop} variant="multicolor" />
        </View>
      </View>
    </View>
  );
}

function ValueView({ index }: { index: number }) {
  return (
    <>
      <StepHeader
        description={<Text style={styles.valueDescriptionEmphasis}>My Scoope no es un contador de calorías,{"\n"}es un planificador de alimentación.</Text>}
        descriptionSecondary="Arma minutas con tus comidas, calendarízalas y sigue tu programación."
        descriptionAccessory={
          <View accessibilityLabel="Comidas, minutas, calendario y programas" style={styles.valueIconRow}>
            <EntityIcon entity="meal" size="intro" />
            <EntityIcon entity="dailyPlan" size="intro" />
            <EntityIcon backgroundColor={`${tokens.color.dailyPlan}80`} entity="dpm" size="intro" />
            <EntityIcon entity="program" size="intro" />
          </View>
        }
        eyebrow="Funciones principales"
        icon={Target}
        index={index}
        title="No improvises,"
        titleAccessory={<View style={[styles.loginTitleChip, styles.valueTitleChip]}><Text style={[styles.loginTitleChipText, styles.valueTitleChipText]}>Planifica.</Text></View>}
        titleStyle={styles.valueTitleText}
      />
      <ExplanationDots index={index} />
    </>
  );
}

function StructureView({ index }: { index: number }) {
  const levels: { detail: string; entity: EntityKind; label: string; sectionTitle?: string }[] = [
    { detail: "Compuesto por alimentos", entity: "meal", label: "Mis Comidas" },
    { detail: "Compuesto por comidas", entity: "dailyPlan", label: "Mis Minutas", sectionTitle: "y arma opciones de minutas" },
  ];
  return (
    <>
      <View style={styles.structureRaisedContent}>
        <StepHeader
          description={null}
          eyebrow="Estructura del sistema"
          icon={LibraryBig}
          index={index}
          showIconAboveTitle
          title="Reúne tus comidas recurrentes"
        />
        <View style={styles.levels}>
          {levels.map((level) => (
            <View key={level.label} style={styles.structureSection}>
              {level.sectionTitle ? <Text style={styles.structureSectionTitle}>{level.sectionTitle}</Text> : null}
              <TopAccentCard accent={tokens.color[level.entity]}>
                <EntityIcon entity={level.entity} size="hero" />
                <View style={styles.levelCopy}>
                  <Text style={styles.levelTitle}>{level.label}</Text>
                  <Text style={styles.levelDetail}>{level.detail}</Text>
                </View>
                {level.entity === "meal" ? (
                  <View accessibilityLabel="Cuatro alimentos" style={styles.entityContentsGrid}>
                    {mealFoodIcons.map((FoodIcon, iconIndex) => (
                      <View key={iconIndex} style={[styles.entityContentsTile, { backgroundColor: tokens.color.food }]}>
                        <FoodIcon color={tokens.color.entityIconForeground} size={13} strokeWidth={2} />
                      </View>
                    ))}
                  </View>
                ) : null}
                {level.entity === "dailyPlan" ? (
                  <View accessibilityLabel="Cuatro comidas" style={styles.entityContentsGrid}>
                    {[0, 1, 2, 3].map((mealIndex) => (
                      <View key={mealIndex} style={[styles.entityContentsTile, { backgroundColor: tokens.color.meal }]}>
                        <Utensils color={tokens.color.entityIconForeground} size={13} strokeWidth={2} />
                      </View>
                    ))}
                  </View>
                ) : null}
              </TopAccentCard>
            </View>
          ))}
        </View>
        <Text style={[styles.description, styles.centeredText, styles.structureClosingText]}>Y luego puedes ajustar tus porciones según tu objetivo nutricional.</Text>
      </View>
      <ExplanationDots index={index} />
    </>
  );
}

function PanelsView({ index }: { index: number }) {
  return (
    <>
      <View style={styles.panelsViewContent}>
        <StepHeader
          description={null}
          eyebrow="Paneles de información"
          icon={Eye}
          index={index}
          showIconAboveTitle
          title={"Gramos de proteína por\nKilo de Peso (PPK)"}
          titleStyle={styles.panelsTitle}
        />
        <View style={styles.levels}>
          <View style={styles.structureSection}>
            <TopAccentCard accent={tokens.color.ppk}>
              <View style={styles.levelCopy}>
                <Text style={styles.levelTitle}>PPK</Text>
                <Text style={styles.levelDetail}>Gramos de proteína por kilo de peso corporal</Text>
              </View>
              <ProteinPerKilogramBadge style={styles.panelsPpkBadge} textSize={17} value={39.36 / 80} />
            </TopAccentCard>
          </View>
          <View style={styles.structureSection}>
            <Text style={styles.structureSectionTitle}>Distribución calórica por macros (Alloc)</Text>
            <TopAccentCard accent={tokens.color.protein} style={styles.panelsAllocationRow}>
              <View style={styles.levelCopy}>
                <Text style={styles.levelTitle}>Alloc</Text>
                <Text style={styles.levelDetail}>Distribución de calorías por macronutriente</Text>
              </View>
              <View style={styles.panelsAllocationPreview}>
                <KpiAllocationBar tone="protein" value={33} />
                <KpiAllocationBar tone="carbs" value={41} />
                <KpiAllocationBar tone="fat" value={26} />
              </View>
            </TopAccentCard>
          </View>
        </View>
        <Text style={[styles.description, styles.centeredText, styles.structureClosingText]}>También verás las calorías y gramos por macros correspondientes.</Text>
      </View>
      <ExplanationDots index={index} />
    </>
  );
}

function PanelsCopyView({ index }: { index: number }) {
  const commitmentDetails = {
    shopping: "Genera tu lista de compra",
    cooking: "Define tus preparaciones",
    training: "Diseña tus minutas según tu entrenamiento",
    nutritionist: "Chequea tu progreso con un profesional",
  } as const;
  return (
    <>
      <View style={styles.panelsViewContent}>
        <StepHeader
          description={null}
          eyebrow="Paneles de información"
          icon={Pin}
          index={index}
          showIconAboveTitle
          title="Mejora tu planificación con compromisos."
          titleStyle={styles.panelsTitle}
        />
        <View style={styles.commitmentCards}>
          {commitmentKinds.map((kind) => {
            const { color, icon: CommitmentIcon, label } = commitmentPresentation[kind];
            return (
              <TopAccentCard accent={color} key={kind} style={styles.commitmentCard}>
                <View style={[styles.commitmentHeroIcon, { backgroundColor: `${color}1A` }]}>
                  <CommitmentIcon color={color} size={22} strokeWidth={1.9} />
                </View>
                <View style={styles.levelCopy}>
                  <Text style={styles.levelTitle}>{label}</Text>
                  <Text style={styles.levelDetail}>{commitmentDetails[kind]}</Text>
                </View>
              </TopAccentCard>
            );
          })}
        </View>
        <Text style={[styles.description, styles.centeredText, styles.structureClosingText, styles.commitmentClosingText]}>Cada uno está relacionado con tus objetivos nutricionales, integrarlos te dará una visión completa.</Text>
      </View>
      <ExplanationDots index={index} />
    </>
  );
}

function ControlView({ index }: { index: number }) {
  const levels: { detail: string; entity: EntityKind; label: string; sectionTitle?: string }[] = [
    { detail: "Compuesto por minutas", entity: "dpm", label: "Mi calendario" },
    { detail: "Compuesto por minutas", entity: "program", label: "Mis programas", sectionTitle: "O planifícalas en programas" },
  ];
  return (
    <>
      <View style={styles.structureRaisedContent}>
        <StepHeader
          description={null}
          eyebrow="Planificación"
          icon={CalendarDays}
          index={index}
          showIconAboveTitle
          title="Asigna minutas en tu calendario"
        />
        <View style={styles.levels}>
          {levels.map((level) => (
            <View key={level.label} style={styles.structureSection}>
              {level.sectionTitle ? <Text style={styles.structureSectionTitle}>{level.sectionTitle}</Text> : null}
              <TopAccentCard accent={level.entity === "dpm" ? `${tokens.color.dailyPlan}80` : tokens.color[level.entity]}>
                <EntityIcon backgroundColor={level.entity === "dpm" ? `${tokens.color.dailyPlan}80` : undefined} entity={level.entity} size="hero" />
                <View style={styles.levelCopy}>
                  <Text style={styles.levelTitle}>{level.label}</Text>
                  <Text style={styles.levelDetail}>{level.detail}</Text>
                </View>
                <View accessibilityLabel="Cuatro minutas" style={styles.entityContentsGrid}>
                  {[0, 1, 2, 3].map((dailyPlanIndex) => (
                    <View key={dailyPlanIndex} style={[styles.entityContentsTile, { backgroundColor: tokens.color.dailyPlan }]}>
                      <ClipboardList color={tokens.color.entityIconForeground} size={13} strokeWidth={2} />
                    </View>
                  ))}
                </View>
              </TopAccentCard>
            </View>
          ))}
        </View>
        <Text style={[styles.description, styles.centeredText, styles.structureClosingText]}>Y luego puedes calendarizar las minutas ya estructuradas.</Text>
      </View>
      <ExplanationDots index={index} />
    </>
  );
}

function ProgressView({ index }: { index: number }) {
  return (
    <>
      <View style={styles.structureRaisedContent}>
        <StepHeader
          description={null}
          eyebrow="Seguimiento"
          icon={Sparkles}
          index={index}
          showIconAboveTitle
          title="Ahorra tiempo con un asistente"
        />
        <View style={[styles.levels, styles.assistanceLevels]}>
          <View style={styles.structureSection}>
            <TopAccentCard accent={tokens.color.carbs}>
              <AssistantGradientIcon size={40} strokeWidth={1.8} />
              <View style={styles.levelCopy}>
                <Text style={styles.levelTitle}>Asistente nutricional</Text>
                <Text style={styles.levelDetail}>Realiza propuestas y ajuste</Text>
              </View>
            </TopAccentCard>
          </View>
          <View style={styles.structureSection}>
            <Text style={styles.structureSectionTitle}>Pide propuestas según tus requerimientos</Text>
            <View style={styles.assistancePlansCard}>
              <Svg aria-hidden height="100%" pointerEvents="none" style={StyleSheet.absoluteFill} width="100%">
                <Defs>
                  <LinearGradient id="onboarding-assistance-plans-gradient" x1="0" x2="1" y1="0" y2="1">
                    <Stop offset="0" stopColor={tokens.color.protein} />
                    <Stop offset="0.5" stopColor={tokens.color.carbs} />
                    <Stop offset="1" stopColor={tokens.color.fat} />
                  </LinearGradient>
                </Defs>
                <Rect fill="url(#onboarding-assistance-plans-gradient)" height="100%" rx={tokens.radius.panel} ry={tokens.radius.panel} width="100%" />
              </Svg>
              <View style={styles.assistancePlansGrid}>
                {(["Free", "Basic", "Pro"] as const).map((plan) => (
                  <View key={plan} style={styles.assistancePlanColumn}>
                    <Text style={styles.assistancePlanEyebrow}>PLAN</Text>
                    <Text style={styles.assistancePlanName}>{plan}</Text>
                  </View>
                ))}
              </View>
              <Text style={styles.assistancePlansCaption}>Las tareas ocupan créditos según su dificultad</Text>
            </View>
          </View>
        </View>
        <Text style={[styles.description, styles.explanationDescription, styles.centeredText, styles.structureClosingText, styles.assistanceClosingText]}>
          Puede realizar ajustes a tus programas o realizar otras tareas en el sistema.
        </Text>
      </View>
      <ExplanationDots
        action={<ContinueChip />}
        index={index}
      />
    </>
  );
}

function DisclosuresView({ index }: { index: number }) {
  const { hideCalculationReviewDisclosure } = useContext(JourneyPresentationContext);
  return (
    <DisclosuresStepLayout index={index}>
      <StepHeader brandedCentered description="My Scoope te entregará algunas minutas personalizadas, pero debe considerar:" eyebrow="" icon={LockKeyhole} index={index} showIconAboveTitle title="Información Importante" titleStyle={styles.disclosuresTitle} />
      <View style={styles.noticeStack}>
        <ExplanationCard body="No diagnostica, trata ni reemplaza atención profesional." icon={HeartPulse} title="No es atención médica" />
        {!hideCalculationReviewDisclosure ? <ExplanationCard body="Los cálculos y propuestas deben revisarse antes de usarse." icon={Eye} title="Revisa antes de aplicar" /> : null}
        <ExplanationCard body="Tú decides qué datos compartes y puedes eliminar tu cuenta." icon={LockKeyhole} style={styles.disclosurePrivacyCard} title="Privacidad y control">
          <View style={styles.disclosurePolicyLinks}>
            <ResponsibleUsePolicyLink label="Leer política de privacidad" onPress={noop} />
            <ResponsibleUsePolicyLink label="Leer términos de uso" onPress={noop} />
            <ResponsibleUsePolicyLink label="Leer política de reembolsos" onPress={noop} />
          </View>
        </ExplanationCard>
      </View>
    </DisclosuresStepLayout>
  );
}

function GoalView({ index }: { index: number }) {
  const controller = useJourneyController();
  const { showGoalOptionsEyebrow, showProfileControlBleed } = useContext(JourneyPresentationContext);
  const profileQuestionStyle = useProfileQuestionStyle();
  const goals = [
    ["fat_loss", "Bajar grasa"],
    ["muscle_gain", "Ganar masa muscular"],
    ["maintenance", "Mantenerme"],
    ["performance", "Rendimiento deportivo"],
    ["healthy_eating", "Comer mejor"],
  ] as const;
  const options = (
    <View style={[styles.optionGrid, showProfileControlBleed && styles.profileControlBleed]}>
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
  );
  return (
    <ProfileStepLayout index={index}>
      <StepHeader description="Tu objetivo orienta el ajuste energético y la referencia inicial de proteína. Siempre podrás cambiarlo." eyebrow="Objetivo nutricional" icon={Target} index={index} title="Define tu objetivo" />
      {showGoalOptionsEyebrow ? (
        <Card style={styles.profileCard}>
          <Text style={profileQuestionStyle}>MI OBJETIVO</Text>
          {options}
        </Card>
      ) : options}
    </ProfileStepLayout>
  );
}

function IdentityView({ index }: { index: number }) {
  const controller = useJourneyController();
  const { conciseSexEyebrow, profileQuestionSpacing, showProfileControlBleed } = useContext(JourneyPresentationContext);
  const profileQuestionStyle = useProfileQuestionStyle();
  return (
    <ProfileStepLayout index={index}>
      <StepHeader description="La edad y el sexo usado para el cálculo forman parte de la estimación de tu gasto basal." eyebrow="Datos para el cálculo" icon={CircleUserRound} index={index} title="Ingresa tus datos personales" />
      <Card style={[styles.profileCard, profileQuestionSpacing > 0 && { gap: profileQuestionSpacing }]}>
        <NativeDateTimeField inputStyle={styles.profileInput} label="Fecha de nacimiento" labelStyle={profileQuestionStyle} maximumValue={localDateValue()} mode="date" onChange={(value) => controller.onChange?.("birthDate", value)} value={controller.values.birthDate} />
        <View accessibilityRole="radiogroup" style={styles.identityChoiceField}>
          <Text style={profileQuestionStyle}>{conciseSexEyebrow ? "Sexo" : "Sexo usado para el cálculo nutricional"}</Text>
          <View style={[styles.identityChoiceRow, showProfileControlBleed && styles.profileControlBleed]}>
            {["Masculino", "Femenino"].map((label, optionIndex) => {
              const value = optionIndex === 0 ? "male" : "female";
              const selected = controller.values.sex === value;
              return (
                <Pressable accessibilityRole="radio" accessibilityState={{ selected }} key={label} onPress={() => controller.onChange?.("sex", value)} style={[styles.trainingFrequencyChip, styles.identityChoiceChip, selected && styles.identityChoiceSelected]}>
                  {selected ? <CreditSelectionBorder id="identity-option-border" shape="identity" /> : null}
                  <Text style={[styles.trainingFrequencyChipLabel, styles.identityChoiceChipLabel, selected && styles.trainingFrequencyChipLabelSelected]}>{label}</Text>
                </Pressable>
              );
            })}
          </View>
        </View>
      </Card>
    </ProfileStepLayout>
  );
}

function MeasurementsView({ index }: { index: number }) {
  const controller = useJourneyController();
  const { profileQuestionSpacing } = useContext(JourneyPresentationContext);
  const profileQuestionStyle = useProfileQuestionStyle();
  return (
    <ProfileStepLayout index={index}>
      <StepHeader description="La altura y el peso permiten estimar tu gasto energético y calcular referencias por kilogramo." eyebrow="Datos para el cálculo" icon={Scale} index={index} title="Ingresa tus medidas actuales" />
      <Card style={styles.profileCard}>
        <View style={[styles.measurementFields, profileQuestionSpacing > 0 && { gap: profileQuestionSpacing }]}>
          <View style={styles.flex}><NativeMeasurementField inputStyle={styles.profileInput} kind="height" label="Altura" labelStyle={profileQuestionStyle} onChange={(value) => controller.onChange?.("height", value)} value={controller.values.height} /></View>
          <View style={styles.flex}><NativeMeasurementField inputStyle={styles.profileInput} kind="weight" label="Peso" labelStyle={profileQuestionStyle} onChange={(value) => controller.onChange?.("weight", value)} value={controller.values.weight} /></View>
        </View>
      </Card>
    </ProfileStepLayout>
  );
}

function ActivityView({ index }: { index: number }) {
  const controller = useJourneyController();
  const { profileQuestionSpacing, showProfileControlBleed } = useContext(JourneyPresentationContext);
  const profileQuestionStyle = useProfileQuestionStyle();
  const activityOptions = [
    ["sedentary", "Sedentaria", "La mayor parte del día sentado"],
    ["light", "Ligera", "Caminatas y movimiento ocasional"],
    ["moderate", "Moderada", "Movimiento frecuente durante la semana"],
    ["high", "Alta", "Movimiento exigente la mayoría de los días"],
    ["very_high", "Muy alta", "Actividad física intensa o doble jornada"],
  ] as const;
  return (
    <ProfileStepLayout index={index}>
      <StepHeader description="Separa el movimiento habitual de los entrenamientos para evitar contarlos dos veces." eyebrow="Datos para el cálculo" icon={Dumbbell} index={index} title="Nivel de actividad" />
      <View accessibilityLabel={`Datos solicitados: ${onboardingNutritionFields.join(", ")}`}>
        <Card style={[styles.profileCard, profileQuestionSpacing > 0 && { gap: profileQuestionSpacing }]}>
          <View style={styles.profileQuestionGroup}>
            <Text style={profileQuestionStyle}>Actividad habitual</Text>
            <View style={[styles.activityList, showProfileControlBleed && styles.profileControlBleed]}>
              {activityOptions.map(([value, label, detail]) => {
                const selected = controller.values.activityLevel === value;
                return (
                <Pressable accessibilityRole="radio" accessibilityState={{ selected }} key={value} onPress={() => controller.onChange?.("activityLevel", value)} style={[styles.activityOption, selected && styles.activityOptionSelected]}>
                  {selected ? <CreditSelectionBorder id="activity-selection-border" shape="lg" /> : null}
                  <View style={styles.flex}><Text style={styles.activityLabel}>{label}</Text><Text style={styles.activityDetail}>{detail}</Text></View>
                  {selected ? <SelectedActivityRadio /> : <View style={styles.radio} />}
                </Pressable>
              );})}
            </View>
          </View>
          <View style={styles.trainingFrequencyField}>
            <Text style={profileQuestionStyle}>Entrenamientos por semana</Text>
            <View style={[styles.trainingFrequencyChips, showProfileControlBleed && styles.profileControlBleed]}>
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
    </ProfileStepLayout>
  );
}

function DietaryChoiceGroup({ idPrefix, options, selectedValue, onChange }: { idPrefix: string; options: readonly (readonly [string, string])[]; selectedValue: string; onChange(value: string): void }) {
  const { contentSizedDietaryChips, showProfileControlBleed } = useContext(JourneyPresentationContext);
  return (
    <View style={[styles.dietaryChoiceGrid, contentSizedDietaryChips && styles.dietaryChoiceGridCentered, showProfileControlBleed && styles.profileControlBleed]}>
      {options.map(([value, label], optionIndex) => {
        const selected = value === selectedValue;
        return (
          <Pressable accessibilityRole="radio" accessibilityState={{ selected }} key={value} onPress={() => onChange(value)} style={[styles.dietaryChoiceChip, contentSizedDietaryChips && styles.dietaryChoiceChipContentSized, selected && styles.dietaryChoiceChipSelected]}>
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
  const { profileQuestionSpacing, progressiveAllergyDetails } = useContext(JourneyPresentationContext);
  const profileQuestionStyle = useProfileQuestionStyle();
  return (
    <ProfileStepLayout index={index} primary="Analizar">
      <StepHeader description="Cuéntanos qué alimentos podemos considerar antes de generar tu primera minuta." eyebrow="Preferencias alimentarias" icon={Leaf} index={index} title="Preferencias alimentarias" />
      <Card style={[styles.profileCard, styles.dietaryCard, profileQuestionSpacing > 0 && { gap: profileQuestionSpacing }]}>
        <View accessibilityRole="radiogroup" style={styles.dietaryQuestion}>
          <Text style={profileQuestionStyle}>Tipo de alimentación</Text>
          <DietaryChoiceGroup idPrefix="diet-type" onChange={(value) => controller.onChange?.("dietaryPattern", value)} options={[["omnivore", "Omnívora"], ["vegetarian", "Vegetariana"], ["vegan", "Vegana"], ["pescatarian", "Pescetariana"], ["flexitarian", "Flexitariana"]]} selectedValue={controller.values.dietaryPattern} />
        </View>
        <View accessibilityRole="radiogroup" style={styles.dietaryQuestion}>
          <Text style={profileQuestionStyle}>Alergias o condiciones relevantes</Text>
          <DietaryChoiceGroup idPrefix="diet-condition" onChange={(value) => controller.onChange?.("allergy", value)} options={[["", "Sin alergias"], ["gluten", "Gluten"], ["lácteos", "Lácteos"], ["frutos secos", "Frutos secos"], ["mariscos", "Mariscos"], ["otra", "Otra"]]} selectedValue={controller.values.allergy} />
          {(!progressiveAllergyDetails || controller.values.allergy === "otra") ? <Field
            autoCapitalize="sentences"
            hideLabel={progressiveAllergyDetails}
            label="Otra alergia o condición (opcional)"
            labelStyle={profileQuestionStyle}
            onChangeText={(value) => controller.onChange?.("allergyDetails", value)}
            placeholder={progressiveAllergyDetails ? "Indícanos tu condición relevante" : "Ej. soya, huevo o condición relevante"}
            value={controller.values.allergyDetails}
          /> : null}
        </View>
        <Field
          autoCapitalize="sentences"
          label="Alimentos que no consumes"
          labelStyle={profileQuestionStyle}
          onChangeText={(value) => controller.onChange?.("avoidedFoods", value)}
          placeholder="Ej. cilantro, aceitunas o champiñones"
          value={controller.values.avoidedFoods}
        />
      </Card>
      {controller.error ? <InlineNotice tone="error">{controller.error}</InlineNotice> : null}
    </ProfileStepLayout>
  );
}

function SummaryView({ index }: { index: number }) {
  const controller = useJourneyController();
  const { profileQuestionSpacing, storyboardSummaryLayout } = useContext(JourneyPresentationContext);
  const profileQuestionStyle = useProfileQuestionStyle();
  const estimate = controller.estimate;
  const calories = Math.round(estimate?.total_kcal ?? 1980);
  const protein = Math.round(estimate?.protein ?? 148);
  const carbs = Math.round(estimate?.carbs ?? 208);
  const fat = Math.round(estimate?.fat ?? 62);
  const allocation = (grams: number, kcalPerGram: number) => Math.round(((grams * kcalPerGram) / Math.max(calories, 1)) * 100);
  const goalLabel = ({ fat_loss: "Bajar grasa", muscle_gain: "Ganar masa muscular", maintenance: "Mantenerme", performance: "Rendimiento", healthy_eating: "Comer mejor" } as Record<string, string>)[controller.values.goal] ?? controller.values.goal;
  const activityLabel = ({ sedentary: "Sedentaria", light: "Ligera", moderate: "Moderada", high: "Alta", very_high: "Muy alta" } as Record<string, string>)[controller.values.activityLevel] ?? controller.values.activityLevel;
  const estimationInformationSection = (
    <View style={[styles.summaryGrid, storyboardSummaryLayout && styles.summaryGridPanelBleed]}>
      <View style={styles.summaryCell}><Text style={styles.summaryLabel}>Objetivo</Text><Text style={styles.summaryText}>{goalLabel}</Text></View>
      <View style={styles.summaryCell}><Text style={styles.summaryLabel}>Referencia</Text><Text style={styles.summaryText}>{controller.values.weight} kg</Text></View>
      <View style={styles.summaryCell}><Text style={styles.summaryLabel}>Actividad</Text><Text style={styles.summaryText}>{activityLabel}</Text></View>
      <View style={styles.summaryCell}><Text style={styles.summaryLabel}>Entrenamiento</Text><Text style={styles.summaryText}>{controller.values.trainingFrequency >= 6 ? "6+" : controller.values.trainingFrequency} días</Text></View>
    </View>
  );
  const maintenanceSection = (
    <View style={[styles.summaryQuestion, storyboardSummaryLayout && styles.summaryMaintenanceCloser]}>
      <View style={styles.summaryHero}>
        <Text style={styles.summaryMetricLabel}>Kcal de mantenimiento{"\n"}estimado</Text>
        <View style={styles.summaryValueGroup}>
          <Text style={styles.summaryValue}>{Math.round(estimate?.estimated_maintenance_kcal ?? 2340).toLocaleString("es-CL")}</Text>
          <Text style={styles.summaryMetricUnit}>kcal</Text>
        </View>
      </View>
    </View>
  );
  const nutritionGoalSection = (
    <View style={styles.summaryQuestion}>
      <Text style={profileQuestionStyle}>OBJETIVO NUTRICIONAL PROPUESTO</Text>
      <NutritionKpiSection
        calories={calories}
        protein={{ allocation: allocation(protein, 4), grams: protein, perKilogram: estimate?.protein_per_kg ?? 1.8 }}
        carbs={{ allocation: allocation(carbs, 4), grams: carbs }}
        fat={{ allocation: allocation(fat, 9), grams: fat }}
      />
    </View>
  );
  return (
    <ProfileStepLayout index={index} primary="Generar primera minuta">
      <StepHeader description="Comprueba los datos y la estimación inicial antes de continuar." eyebrow="Resumen de la ficha" icon={Gauge} index={index} title="Revisa tu información" />
      <Card style={[styles.profileCard, styles.summaryCard, profileQuestionSpacing > 0 && { gap: profileQuestionSpacing }]}>
        {estimationInformationSection}
        {maintenanceSection}
        {nutritionGoalSection}
        {!storyboardSummaryLayout ? <Pressable accessibilityRole="button" onPress={controller.onAdjust ?? noop} style={styles.adjustNutritionAction}>
          <Text style={styles.adjustNutritionLabel}>Ajusta objetivo nutricional</Text>
        </Pressable> : null}
      </Card>
      {controller.error ? <InlineNotice tone="error">{controller.error}</InlineNotice> : null}
    </ProfileStepLayout>
  );
}

const generatedDailyPlanReferenceWeightKg = 82;

const generatedDailyPlanMeals: MealPanelItem[] = [
  { id: "generated-breakfast", name: "Desayuno energético", time: "08:00", foods: [{ name: "Avena", quantity: 70, quantityUnit: "g" }, { name: "Yogur griego", quantity: 180, quantityUnit: "g" }, { name: "Arándanos", quantity: 80, quantityUnit: "g" }], calories: 515, calorieShare: 28, proteinGrams: 31, proteinPerKilogram: 31 / generatedDailyPlanReferenceWeightKg, carbsGrams: 67, fatGrams: 14, proteinAllocation: 24, carbsAllocation: 52, fatAllocation: 24 },
  { id: "generated-lunch", name: "Almuerzo balanceado", time: "13:30", foods: [{ name: "Pechuga de pollo", quantity: 170, quantityUnit: "g" }, { name: "Arroz integral", quantity: 160, quantityUnit: "g" }, { name: "Ensalada mixta", quantity: 150, quantityUnit: "g" }], calories: 710, calorieShare: 39, proteinGrams: 58, proteinPerKilogram: 58 / generatedDailyPlanReferenceWeightKg, carbsGrams: 76, fatGrams: 19, proteinAllocation: 33, carbsAllocation: 43, fatAllocation: 24 },
  { id: "generated-dinner", name: "Cena liviana", time: "20:00", foods: [{ name: "Salmón", quantity: 150, quantityUnit: "g" }, { name: "Papas asadas", quantity: 180, quantityUnit: "g" }, { name: "Verduras salteadas", quantity: 160, quantityUnit: "g" }], calories: 615, calorieShare: 33, proteinGrams: 41, proteinPerKilogram: 41 / generatedDailyPlanReferenceWeightKg, carbsGrams: 62, fatGrams: 22, proteinAllocation: 27, carbsAllocation: 40, fatAllocation: 33 },
];

const generatedDailyPlanMealDetails: DailyPlanMealDetailItem[] = [
  {
    id: "generated-breakfast-detail",
    name: "Desayuno energético",
    time: "08:00",
    foods: [
      { id: "generated-oats", name: "Avena", quantity: 70, quantityUnit: "g", calories: 272, calorieShare: 53, proteinGrams: 9, proteinPerKilogram: 9 / generatedDailyPlanReferenceWeightKg, carbsGrams: 46, fatGrams: 5, proteinAllocation: 13, carbsAllocation: 68, fatAllocation: 19 },
      { id: "generated-yogurt", name: "Yogur griego y arándanos", quantity: 260, quantityUnit: "g", calories: 243, calorieShare: 47, proteinGrams: 22, proteinPerKilogram: 22 / generatedDailyPlanReferenceWeightKg, carbsGrams: 21, fatGrams: 9, proteinAllocation: 36, carbsAllocation: 35, fatAllocation: 29 },
    ],
    nutrition: { calories: 515, protein: { allocation: 24, grams: 31, perKilogram: 0.38 }, carbs: { allocation: 52, grams: 67 }, fat: { allocation: 24, grams: 14 } },
  },
  {
    id: "generated-lunch-detail",
    name: "Almuerzo balanceado",
    time: "13:30",
    foods: [
      { id: "generated-chicken", name: "Pechuga de pollo", quantity: 170, quantityUnit: "g", calories: 281, calorieShare: 40, proteinGrams: 53, proteinPerKilogram: 53 / generatedDailyPlanReferenceWeightKg, carbsGrams: 0, fatGrams: 6, proteinAllocation: 76, carbsAllocation: 0, fatAllocation: 24 },
      { id: "generated-rice-salad", name: "Arroz integral y ensalada", quantity: 310, quantityUnit: "g", calories: 429, calorieShare: 60, proteinGrams: 5, proteinPerKilogram: 5 / generatedDailyPlanReferenceWeightKg, carbsGrams: 76, fatGrams: 13, proteinAllocation: 5, carbsAllocation: 71, fatAllocation: 24 },
    ],
    nutrition: { calories: 710, protein: { allocation: 33, grams: 58, perKilogram: 0.7 }, carbs: { allocation: 43, grams: 76 }, fat: { allocation: 24, grams: 19 } },
  },
  {
    id: "generated-dinner-detail",
    name: "Cena liviana",
    time: "20:00",
    foods: [
      { id: "generated-salmon", name: "Salmón", quantity: 150, quantityUnit: "g", calories: 312, calorieShare: 51, proteinGrams: 33, proteinPerKilogram: 33 / generatedDailyPlanReferenceWeightKg, carbsGrams: 0, fatGrams: 20, proteinAllocation: 42, carbsAllocation: 0, fatAllocation: 58 },
      { id: "generated-potatoes-vegetables", name: "Papas y verduras", quantity: 340, quantityUnit: "g", calories: 303, calorieShare: 49, proteinGrams: 8, proteinPerKilogram: 8 / generatedDailyPlanReferenceWeightKg, carbsGrams: 62, fatGrams: 2, proteinAllocation: 11, carbsAllocation: 82, fatAllocation: 7 },
    ],
    nutrition: { calories: 615, protein: { allocation: 27, grams: 41, perKilogram: 0.5 }, carbs: { allocation: 40, grams: 62 }, fat: { allocation: 33, grams: 22 } },
  },
];

function GeneratedDailyPlanView() {
  const controller = useJourneyController();
  if (controller.proposal?.dailyplan) {
    return (
      <>
        <StepHeader description="Revisa la minuta generada antes de guardarla en tu biblioteca." eyebrow="Minuta del día" icon={BookOpen} index={13} showProgress={false} title="Tu primera minuta diaria" />
        <ProposalDailyPlanCard dailyplan={controller.proposal.dailyplan} showNutrition={false} />
        {controller.error ? <InlineNotice tone="error">{controller.error}</InlineNotice> : null}
        <CreditContinueButton />
        <View style={styles.generatedDailyPlanBottomSpacing} />
      </>
    );
  }
  return (
    <>
      <EntityDetailPage
        entity="dailyPlan"
        eyebrow="MINUTA DEL DÍA"
        indicators={[{ icon: "meal", label: "comidas", value: 3 }, { icon: "food", label: "alimentos", value: 9 }]}
        nutrition={{
          calories: 1840,
          protein: { allocation: 28, grams: 130, perKilogram: 1.6 },
          carbs: { allocation: 45, grams: 205 },
          fat: { allocation: 27, grams: 55 },
        }}
        title="Minuta equilibrada · Día 1">
        <EntityDetailSection title="Composición de la minuta diaria">
          <MealPanels items={generatedDailyPlanMeals} showEditTab={false} />
        </EntityDetailSection>
        <ProgramSectionHeader icon={Utensils} subtitle="Revisa el detalle de comida en esta minuta diaria. Conoce sus alimentos, compáralos, y ve su impacto real en la comida." title="Detalle de cada Comida" />
        <DailyPlanMealDetailList items={generatedDailyPlanMealDetails} />
      </EntityDetailPage>
      <CreditContinueButton />
      <View style={styles.generatedDailyPlanBottomSpacing} />
    </>
  );
}

const plans = [
  { accent: tokens.color.fat, caption: "Incluido sin costo.", name: "Free", price: "Gratis" },
  { accent: tokens.color.carbs, name: "Basic", price: "Ver precio en la tienda" },
  { accent: tokens.color.protein, name: "Pro", price: "Ver precio en la tienda" },
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
              <SubscriptionPurchaseButton label={`Ver opciones de ${plan.name}`} onPress={() => controller.onChoosePlan?.(plan.name)} />
            )}
          </SubscriptionPlanCard>
        ))}
      </View>
      {controller.error ? <InlineNotice tone="error">{controller.error}</InlineNotice> : null}
      <Text style={styles.quietCenter}>Los precios y periodos vigentes se muestran directamente desde la tienda antes de comprar.</Text>
    </>
  );
}

const views: Record<OnboardingJourneyStep, (props: { index: number }) => ReactNode> = {
  login: LoginView,
  value: ValueView,
  structure: StructureView,
  panels: PanelsView,
  panelsCopy: PanelsCopyView,
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

export function OnboardingJourneyView({
  conciseSexEyebrow = false,
  contentSizedDietaryChips = false,
  controller,
  disclosuresTitleSpacingReduction = 0,
  fixedDisclosuresFooter = false,
  fixedLoginActionBottomSpacing = 0,
  fixedProfileChrome = false,
  fixedProfileFooterBottomSpacing = 0,
  fullWidthExplanationTransition = false,
  hideCalculationReviewDisclosure = false,
  progressiveAllergyDetails = false,
  profileEyebrowsMuted = false,
  profileProgressBottomSpacing = 0,
  profileProgressEyebrowBottomSpacing = 0,
  profileQuestionSpacing = 0,
  profileProgressWidthReduction = 0,
  profileTitleBottomSpacingReduction = 0,
  showGoalOptionsEyebrow = false,
  showProfileControlBleed = false,
  storyboardSummaryLayout = false,
  step,
  topInsetReduction = 0,
}: {
  conciseSexEyebrow?: boolean;
  contentSizedDietaryChips?: boolean;
  controller?: OnboardingJourneyController;
  disclosuresTitleSpacingReduction?: number;
  fixedDisclosuresFooter?: boolean;
  fixedLoginActionBottomSpacing?: number;
  fixedProfileChrome?: boolean;
  fixedProfileFooterBottomSpacing?: number;
  fullWidthExplanationTransition?: boolean;
  hideCalculationReviewDisclosure?: boolean;
  progressiveAllergyDetails?: boolean;
  profileEyebrowsMuted?: boolean;
  profileProgressBottomSpacing?: number;
  profileProgressEyebrowBottomSpacing?: number;
  profileQuestionSpacing?: number;
  profileProgressWidthReduction?: number;
  profileTitleBottomSpacingReduction?: number;
  showGoalOptionsEyebrow?: boolean;
  showProfileControlBleed?: boolean;
  storyboardSummaryLayout?: boolean;
  step: OnboardingJourneyStep;
  topInsetReduction?: number;
}) {
  const index = onboardingJourneySteps.findIndex((item) => item.key === step);
  const ViewComponent = views[step];
  const resolvedController = useMemo(() => controller ?? { values: onboardingJourneyPreviewValues }, [controller]);
  const { width } = useWindowDimensions();
  const [translateX] = useState(() => new Animated.Value(0));
  const [transitioning, setTransitioning] = useState(false);
  const [explanationTransitionWidth, setExplanationTransitionWidth] = useState(width);
  const interactiveExplanation = Boolean(controller) && index >= 1 && index <= 6;
  const transitionWidth = fullWidthExplanationTransition ? explanationTransitionWidth : width;
  const explanationPageGap = 48;
  const explanationStride = transitionWidth + explanationPageGap;
  const explanationOffset = -(index - 1) * explanationStride;
  const handleExplanationViewportLayout = useCallback((event: LayoutChangeEvent) => {
    if (!fullWidthExplanationTransition) return;
    setExplanationTransitionWidth(event.nativeEvent.layout.width);
  }, [fullWidthExplanationTransition]);
  useLayoutEffect(() => {
    translateX.setValue(explanationOffset);
  }, [explanationOffset, translateX]);
  const moveToExplanation = useCallback((direction: "back" | "next") => {
    if (transitioning) return;
    const canMove = direction === "next" ? index < 6 : index > 1;
    if (!canMove) {
      Animated.spring(translateX, { damping: 20, stiffness: 220, toValue: explanationOffset, useNativeDriver: true }).start();
      return;
    }
    setTransitioning(true);
    const destination = explanationOffset + (direction === "next" ? -explanationStride : explanationStride);
    Animated.timing(translateX, { duration: 220, toValue: destination, useNativeDriver: true }).start(({ finished }) => {
      if (finished) {
        if (direction === "next") resolvedController.onNext?.();
        else resolvedController.onBack?.();
      }
      setTransitioning(false);
    });
  }, [explanationOffset, explanationStride, index, resolvedController, transitioning, translateX]);
  const finishExplanationGesture = useCallback((gesture: PanResponderGestureState) => {
    if (gesture.dx <= -48 || gesture.vx <= -0.45) moveToExplanation("next");
    else if (gesture.dx >= 48 || gesture.vx >= 0.45) moveToExplanation("back");
    else Animated.spring(translateX, { damping: 20, stiffness: 220, toValue: explanationOffset, useNativeDriver: true }).start();
  }, [explanationOffset, moveToExplanation, translateX]);
  const swipeResponder = useMemo(() => PanResponder.create({
    onMoveShouldSetPanResponder: (_event, gesture) => interactiveExplanation && Math.abs(gesture.dx) > 12 && Math.abs(gesture.dx) > Math.abs(gesture.dy),
    onMoveShouldSetPanResponderCapture: (_event, gesture) => interactiveExplanation && Math.abs(gesture.dx) > 12 && Math.abs(gesture.dx) > Math.abs(gesture.dy),
    onPanResponderMove: (_event, gesture) => {
      if (transitioning) return;
      const atBoundary = (index === 1 && gesture.dx > 0) || (index === 6 && gesture.dx < 0);
      translateX.setValue(explanationOffset + gesture.dx * (atBoundary ? 0.18 : 1));
    },
    onPanResponderRelease: (_event, gesture) => finishExplanationGesture(gesture),
    onPanResponderTerminate: (_event, gesture) => finishExplanationGesture(gesture),
  }), [explanationOffset, finishExplanationGesture, index, interactiveExplanation, transitioning, translateX]);
  if (interactiveExplanation) {
    return (
      <JourneyControllerContext.Provider value={resolvedController}>
        <JourneyPresentationContext.Provider value={{ conciseSexEyebrow, contentSizedDietaryChips, disclosuresTitleSpacingReduction, externalExplanationChrome: true, fixedDisclosuresFooter, fixedLoginActionBottomSpacing, fixedProfileChrome, fixedProfileFooterBottomSpacing, hideCalculationReviewDisclosure, progressiveAllergyDetails, profileEyebrowsMuted, profileProgressBottomSpacing, profileProgressEyebrowBottomSpacing, profileQuestionSpacing, profileProgressWidthReduction, profileTitleBottomSpacingReduction, showGoalOptionsEyebrow, showProfileControlBleed, storyboardSummaryLayout }}>
          <View style={[styles.screen, styles.interactiveExplanationScreen, topInsetReduction > 0 && { paddingTop: styles.screen.paddingTop - topInsetReduction }, styles.interactiveExplanationScreenFlush]}>
            <View style={[styles.centeredLogo, styles.explanationLogo]}><MyScoopeBrandLogo scale={0.88} /></View>
            <View
              {...swipeResponder.panHandlers}
              onLayout={handleExplanationViewportLayout}
              style={[styles.explanationViewport, fullWidthExplanationTransition && styles.fullWidthExplanationViewport]}
            >
              <Animated.View style={[styles.explanationTrack, { transform: [{ translateX }], width: transitionWidth * explanationSteps.length + explanationPageGap * (explanationSteps.length - 1) }] }>
                {explanationSteps.map((pageStep, explanationIndex) => {
                  const pageIndex = explanationIndex + 1;
                  const PageView = views[pageStep.key];
                  return (
                    <View
                      key={pageStep.key}
                      style={[styles.explanationPage, { width: transitionWidth }]}
                    >
                      <ScrollView
                        bounces={false}
                        contentContainerStyle={styles.explanationScrollContent}
                        nestedScrollEnabled
                        removeClippedSubviews={false}
                        showsVerticalScrollIndicator={false}
                        style={styles.explanationPageScroll}>
                        <View style={[styles.explanationSlide, fullWidthExplanationTransition && styles.fullWidthExplanationSlide]}>
                          <PageView index={pageIndex} />
                        </View>
                      </ScrollView>
                    </View>
                  );
                })}
              </Animated.View>
            </View>
            <ExplanationDots action={index === 6 ? <ContinueChip /> : undefined} compact forceVisible index={index} />
          </View>
        </JourneyPresentationContext.Provider>
      </JourneyControllerContext.Provider>
    );
  }
  return (
    <JourneyControllerContext.Provider value={resolvedController}>
      <JourneyPresentationContext.Provider value={{ conciseSexEyebrow, contentSizedDietaryChips, disclosuresTitleSpacingReduction, externalExplanationChrome: false, fixedDisclosuresFooter, fixedLoginActionBottomSpacing, fixedProfileChrome, fixedProfileFooterBottomSpacing, hideCalculationReviewDisclosure, progressiveAllergyDetails, profileEyebrowsMuted, profileProgressBottomSpacing, profileProgressEyebrowBottomSpacing, profileQuestionSpacing, profileProgressWidthReduction, profileTitleBottomSpacingReduction, showGoalOptionsEyebrow, showProfileControlBleed, storyboardSummaryLayout }}>
        <View
          style={[
            styles.screen,
            index === 0 && styles.loginBackgroundScreen,
            fixedLoginActionBottomSpacing > 0 && index === 0 && styles.fixedLoginScreen,
            index >= 8 && index <= 13 && styles.profileScreen,
            fixedDisclosuresFooter && index === 7 && styles.fixedProfileScreen,
            fixedProfileChrome && index >= 8 && index <= 13 && styles.fixedProfileScreen,
            topInsetReduction > 0 && {
              paddingTop: (index >= 8 && index <= 13 ? styles.profileScreen.paddingTop : styles.screen.paddingTop) - topInsetReduction,
            },
          ]}
        >
          <ViewComponent index={index} />
        </View>
      </JourneyPresentationContext.Provider>
    </JourneyControllerContext.Provider>
  );
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, gap: tokens.spacing.lg, minHeight: 690, paddingBottom: tokens.spacing.xl, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg + (tokens.spacing.md * 2) + 18 },
  interactiveExplanationScreen: { flex: 1 },
  interactiveExplanationScreenFlush: { paddingTop: 76 },
  fixedLoginScreen: { flex: 1, minHeight: 0 },
  loginBackgroundScreen: { flex: 1, minHeight: 0, overflow: "hidden" },
  loginLogo: { marginBottom: -18, marginTop: 62 },
  loginImageStage: { height: 396, position: "relative", width: "100%" },
  loginBackgroundImage: { bottom: 0, height: 396, left: 0, position: "absolute", right: 0, top: 0, width: "100%" },
  loginContent: { flex: 1, gap: tokens.spacing.lg, transform: [{ translateY: -12 }], zIndex: 1 },
  explanationViewport: { flex: 1, overflow: "hidden", width: "100%" },
  explanationTrack: { flexDirection: "row", flexShrink: 0, gap: 48, height: "100%" },
  explanationPage: { flexShrink: 0, height: "100%", overflow: "hidden" },
  explanationPageScroll: { flex: 1, width: "100%" },
  explanationScrollContent: { flexGrow: 1 },
  explanationSlide: { flex: 1, gap: tokens.spacing.lg, justifyContent: "center", paddingTop: tokens.spacing.xxl - 18 },
  fullWidthExplanationViewport: { alignSelf: "stretch", marginHorizontal: -tokens.spacing.screen, width: undefined },
  fullWidthExplanationSlide: { paddingHorizontal: tokens.spacing.screen },
  profileScreen: { paddingTop: tokens.spacing.lg + (tokens.spacing.md * 2) + 18 - 32 },
  fixedProfileScreen: { flex: 1, minHeight: 0 },
  fixedProfileLayout: { flex: 1, minHeight: 0 },
  fixedProfileScroll: { flex: 1, marginHorizontal: -tokens.spacing.screen },
  disclosuresScroll: { marginTop: -12 },
  fixedProfileScrollContent: { gap: tokens.spacing.lg, paddingBottom: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen },
  intro: { alignItems: "flex-start", gap: tokens.spacing.sm },
  introCentered: { alignItems: "center" },
  centeredLogo: { alignItems: "center", justifyContent: "center", width: "100%" },
  disclosuresLogo: { marginBottom: 12 },
  explanationLogo: { marginBottom: -20 },
  centeredText: { textAlign: "center" },
  centeredTitleSpacing: { marginBottom: tokens.spacing.sm, marginTop: tokens.spacing.xxl + tokens.spacing.md },
  stepMeta: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, width: "100%" },
  stepCount: { color: tokens.color.textSoft, fontSize: 10, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, letterSpacing: 1 },
  progressTrack: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, flex: 1, height: 3, overflow: "hidden" },
  progressFill: { backgroundColor: tokens.color.interactivePrimary, height: "100%" },
  iconWell: { alignItems: "center", height: 54, justifyContent: "center", marginTop: tokens.spacing.sm, width: 54 },
  eyebrow: { color: tokens.color.interactivePrimary, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.2, textTransform: "uppercase" },
  disclosuresEyebrow: { color: tokens.color.textMuted },
  disclosuresTitle: { marginTop: 0 },
  title: { color: tokens.color.textMain, fontSize: 28, fontWeight: tokens.weight.extraBold, letterSpacing: -0.8, lineHeight: 32 },
  description: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  disclosuresDescription: { color: tokens.color.textMain, fontWeight: tokens.weight.semibold },
  valueDescription: { fontSize: 18, lineHeight: 26 },
  valueDescriptionEmphasis: { fontWeight: tokens.weight.bold },
  valueSecondaryDescription: { marginTop: 28 },
  valueIconRow: { alignItems: "center", alignSelf: "center", flexDirection: "row", gap: tokens.spacing.md, marginTop: tokens.spacing.lg + 24 },
  explanationDescription: { color: tokens.color.textMain },
  assistancePlansCard: { borderRadius: tokens.radius.panel, height: 118, marginLeft: tokens.spacing.md, overflow: "hidden", paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.lg, width: "100%" },
  assistancePlansGrid: { flexDirection: "row", gap: tokens.spacing.sm, marginRight: -20, paddingHorizontal: 10 },
  assistancePlanColumn: { flex: 1, minWidth: 0 },
  assistancePlanEyebrow: { color: tokens.color.surfaceApp, fontSize: 9, fontWeight: tokens.weight.bold, letterSpacing: 0.8, lineHeight: 11, opacity: 0.72 },
  assistancePlanName: { color: tokens.color.surfaceApp, fontSize: 22, fontWeight: tokens.weight.bold, lineHeight: 26 },
  assistancePlansCaption: { alignSelf: "stretch", color: tokens.color.surfaceApp, fontSize: 11, fontWeight: tokens.weight.medium, lineHeight: 15, marginTop: tokens.spacing.lg - 8, textAlign: "center", transform: [{ translateX: -tokens.spacing.md }] },
  descriptionEmphasis: { fontWeight: tokens.weight.bold },
  footer: { gap: tokens.spacing.sm, marginTop: "auto" },
  disclosuresConfirmationSpacing: { marginVertical: 4 },
  explanationFooter: { alignItems: "center", gap: tokens.spacing.md, marginBottom: 48, marginTop: "auto" },
  explanationFooterCompact: { marginBottom: 28, marginTop: -16 },
  explanationFooterWithAction: { position: "relative", width: "100%" },
  explanationFooterAction: { position: "absolute", right: 0, top: 3 },
  explanationDots: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "center", minHeight: 40 },
  explanationDot: { backgroundColor: tokens.color.borderStrong, borderRadius: 4.5, height: 9, overflow: "hidden", width: 9 },
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
  profileProgressLineActive: { backgroundColor: tokens.color.carbs },
  profileProgressDot: { backgroundColor: tokens.color.borderStrong, borderRadius: 7, height: 14, width: 14 },
  profileProgressDotActive: { backgroundColor: tokens.color.carbs },
  backAction: { alignItems: "center", alignSelf: "center", flexDirection: "row", gap: tokens.spacing.xs, minHeight: 40, paddingHorizontal: tokens.spacing.md },
  disclosuresBackAction: { marginBottom: 20 },
  profileFooter: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  profileBackAction: { alignSelf: "auto", paddingLeft: 0 },
  profilePrimaryAction: { minWidth: 144 },
  backLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  explanationCard: { backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.lg, paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.screen },
  disclosurePrivacyCard: { paddingBottom: tokens.spacing.screen - 8 },
  explanationCardRow: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md },
  explanationIcon: { alignItems: "center", backgroundColor: tokens.color.surfaceElevated, borderRadius: tokens.radius.md, height: 36, justifyContent: "center", width: 36 },
  explanationCopy: { flex: 1, gap: tokens.spacing.sm },
  explanationTitle: { color: tokens.color.textMain, fontSize: 18, fontWeight: tokens.weight.bold, lineHeight: 22 },
  explanationBody: { color: tokens.color.textMuted, fontSize: 14, lineHeight: 20 },
  disclosurePolicyLinks: { alignItems: "center", marginTop: tokens.spacing.md },
  loginHero: { alignItems: "center", gap: tokens.spacing.md, marginTop: -12 },
  loginDescription: { color: tokens.color.textMain, marginBottom: 22, marginTop: -10 },
  loginAction: { width: "100%" },
  loginKicker: { color: tokens.color.program, fontSize: 11, fontWeight: tokens.weight.extraBold, letterSpacing: 1.5 },
  loginTitleRow: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: 7, justifyContent: "center", marginBottom: tokens.spacing.sm },
  loginTitle: { color: tokens.color.textMain, fontSize: 32, fontWeight: tokens.weight.extraBold, letterSpacing: -1, lineHeight: 37, textAlign: "center" },
  loginTitleChip: { backgroundColor: tokens.color.textMain, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 1 },
  loginTitleChipText: { color: tokens.color.surfaceApp, fontSize: 30, fontWeight: tokens.weight.extraBold, letterSpacing: -1, lineHeight: 35 },
  valueTitleText: { fontSize: 37, lineHeight: 43 },
  valueTitleChip: { marginBottom: 48, marginTop: -10 },
  valueTitleChipText: { fontSize: 52, lineHeight: 61 },
  cardTitle: { color: tokens.color.textMain, fontSize: 19, fontWeight: tokens.weight.bold },
  quietCenter: { color: tokens.color.textSoft, fontSize: 11, lineHeight: 16, textAlign: "center" },
  levels: { gap: tokens.spacing.xl + 24, marginTop: -tokens.spacing.sm },
  assistanceLevels: { width: "100%" },
  structureRaisedContent: { gap: tokens.spacing.lg, transform: [{ translateY: -40 }] },
  structureSection: { gap: tokens.spacing.md },
  structureSectionTitle: { color: tokens.color.textMain, fontSize: 28, fontWeight: tokens.weight.extraBold, lineHeight: 32, textAlign: "center" },
  structureClosingText: { color: tokens.color.textMain, marginTop: 40 - tokens.spacing.md },
  assistanceClosingText: { marginTop: -tokens.spacing.md },
  panelsViewContent: { gap: 20, transform: [{ translateY: -40 }] },
  panelsTitle: { marginBottom: 0 },
  panelsAllocationPreview: { gap: 10, width: 100 },
  panelsAllocationRow: { alignItems: "flex-start", columnGap: 20 },
  panelsPpkBadge: { borderRadius: 10, minHeight: 29, paddingHorizontal: 10 },
  levelRowFrame: { borderRadius: tokens.radius.panel, marginHorizontal: tokens.spacing.md, overflow: "hidden" },
  levelRow: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderTopLeftRadius: tokens.radius.panel - 3, borderTopRightRadius: tokens.radius.panel - 3, flexDirection: "row", gap: tokens.spacing.md, marginTop: 3, padding: tokens.spacing.screen },
  entityContentsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 4, width: 44 },
  commitmentCards: { gap: 12, marginTop: 8 },
  commitmentClosingText: { marginTop: 0 },
  commitmentCard: { minHeight: 44 + tokens.spacing.screen * 2 },
  commitmentHeroIcon: { alignItems: "center", borderRadius: 10, height: 40, justifyContent: "center", width: 40 },
  entityContentsTile: { alignItems: "center", borderRadius: 6, height: 20, justifyContent: "center", width: 20 },
  levelCopy: { flex: 1, gap: 2, minWidth: 0 },
  levelTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.bold, lineHeight: 24 },
  levelDetail: { color: tokens.color.textMuted, fontSize: 11, lineHeight: 15 },
  metricRow: { alignItems: "baseline", flexDirection: "row", justifyContent: "space-between" },
  metricLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  metricValue: { color: tokens.color.textMain, fontSize: 28, fontWeight: tokens.weight.extraBold },
  metricTrack: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, height: 10, overflow: "hidden" },
  metricFill: { backgroundColor: tokens.color.success, borderRadius: tokens.radius.pill, height: "100%", width: "86%" },
  progressFacts: { gap: tokens.spacing.sm, marginTop: tokens.spacing.sm },
  noticeStack: { gap: tokens.spacing.sm },
  optionGrid: { gap: tokens.spacing.sm },
  profileControlBleed: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  optionCard: { alignItems: "center", backgroundColor: "transparent", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.lg, borderWidth: 1, flexDirection: "row", justifyContent: "space-between", minHeight: 50, paddingHorizontal: tokens.spacing.lg },
  optionCardSelected: { backgroundColor: tokens.color.surfaceElevated, borderColor: "transparent", borderWidth: 0, overflow: "hidden" },
  optionText: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  optionTextSelected: { color: tokens.color.textMain },
  goalSelectionCheck: { height: 22, width: 22 },
  measurementFields: { gap: tokens.spacing.md },
  profileCard: { backgroundColor: "transparent" },
  summaryCard: { marginTop: -tokens.spacing.xs },
  profileInput: { paddingVertical: 0, textAlign: "center", textAlignVertical: "center" },
  identityChoiceField: { gap: 7 },
  identityChoiceRow: { flexDirection: "row", gap: tokens.spacing.sm },
  identityChoiceChip: { minHeight: 44 },
  identityChoiceChipLabel: { fontSize: 16, lineHeight: 20 },
  identityChoiceSelected: { backgroundColor: tokens.color.surfaceElevated, borderColor: "transparent", borderWidth: 0, overflow: "hidden" },
  flex: { flex: 1 },
  fieldLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  profileQuestion: { color: tokens.color.textMain, fontSize: tokens.type.label, fontWeight: tokens.weight.regular, letterSpacing: 1.1, textTransform: "uppercase" },
  profileQuestionMuted: { color: tokens.color.textMuted },
  profileQuestionGroup: { gap: 7 },
  activityList: { gap: tokens.spacing.sm },
  activityOption: { alignItems: "center", borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.md, padding: tokens.spacing.md },
  activityOptionSelected: { backgroundColor: tokens.color.surfaceElevated, borderColor: "transparent", borderWidth: 0, overflow: "hidden" },
  activityLabel: { color: tokens.color.textMain, fontSize: 14, fontWeight: tokens.weight.bold },
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
  dietaryChoiceGridCentered: { justifyContent: "center" },
  dietaryChoiceChip: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, flexBasis: "30%", flexGrow: 1, justifyContent: "center", minHeight: 34, minWidth: 0, paddingHorizontal: tokens.spacing.sm },
  dietaryChoiceChipContentSized: { flexBasis: "auto", flexGrow: 0, paddingHorizontal: tokens.spacing.xl },
  dietaryChoiceChipSelected: { backgroundColor: tokens.color.surfaceElevated, borderColor: "transparent", borderWidth: 0, overflow: "hidden" },
  summaryHero: { alignItems: "center", backgroundColor: tokens.color.kcalSurface, borderColor: tokens.color.kcalBorder, borderRadius: tokens.component.nutritionKpi.regular.totalRadius, borderWidth: tokens.component.nutritionKpi.regular.totalBorderWidth, flexDirection: "row", gap: tokens.spacing.md, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 76, paddingHorizontal: tokens.spacing.lg, paddingVertical: tokens.spacing.sm },
  summaryValueGroup: { alignItems: "flex-end" },
  summaryValue: { color: tokens.color.textMain, fontSize: 24, fontWeight: tokens.weight.extraBold, letterSpacing: -0.5, lineHeight: 28 },
  summaryGrid: { alignSelf: "stretch", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  summaryGridPanelBleed: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  summaryQuestion: { gap: 7 },
  summaryMaintenanceCloser: { marginBottom: tokens.spacing.sm, marginTop: -tokens.spacing.md },
  summaryCell: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, flexBasis: "45%", flexGrow: 1, gap: 3, minWidth: 0, padding: tokens.spacing.sm },
  summaryLabel: { color: tokens.color.textSoft, fontSize: 11, lineHeight: 14, textTransform: "uppercase" },
  summaryText: { color: tokens.color.textMain, fontSize: 16, fontWeight: tokens.weight.bold, lineHeight: 20 },
  summaryMetricLabel: { color: tokens.color.textMain, flex: 1, fontSize: 16, fontWeight: tokens.weight.semibold, lineHeight: 20, minWidth: 0 },
  summaryMetricUnit: { color: tokens.color.textSoft, fontSize: 11, fontWeight: tokens.weight.medium },
  generatedDailyPlanBottomSpacing: { height: 40 },
  adjustNutritionAction: { alignItems: "center", justifyContent: "center", minHeight: 40, paddingHorizontal: tokens.spacing.md },
  adjustNutritionLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium },
  planList: { gap: tokens.spacing.sm },
});
