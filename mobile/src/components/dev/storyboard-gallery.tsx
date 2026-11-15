import { useState, type ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { LabelCaptureStoryboardView, labelCaptureStoryboardSteps } from "@/components/label-capture";
import { OnboardingJourneyView, onboardingJourneySteps, topInsetReductionForOnboardingStoryboard } from "@/components/onboarding";
import { SubscriptionPreviewContent } from "@/components/dev/subscription-gallery";
import { InlineNotice, ScrollableTabBar, SectionTitle } from "@/components/ui";
import { tokens } from "@/design/tokens";

const previewWidths = [
  { label: "iPhone XR", width: 414 },
  { label: "Teléfono compacto", width: 375 },
] as const;

type PreviewWidth = (typeof previewWidths)[number]["width"];

function StoryboardGallery<K extends string>({
  accessibilityLabel,
  detail,
  featuredStep,
  notice,
  renderStep,
  steps,
  title,
}: {
  accessibilityLabel: string;
  detail: string;
  featuredStep?: K;
  notice: string;
  renderStep(step: K): ReactNode;
  steps: readonly { key: K; label: string }[];
  title: string;
}) {
  const [previewWidth, setPreviewWidth] = useState<PreviewWidth>(414);
  const orderedSteps = featuredStep
    ? [...steps.filter((step) => step.key === featuredStep), ...steps.filter((step) => step.key !== featuredStep)]
    : steps;

  return (
    <>
      <SectionTitle detail={detail} title={title} />
      <ScrollableTabBar<PreviewWidth>
        accessibilityLabel={accessibilityLabel}
        activeTab={previewWidth}
        density="compact"
        onChange={setPreviewWidth}
        tabs={previewWidths.map((preview) => ({ key: preview.width, label: preview.label }))}
      />
      <InlineNotice>{notice}</InlineNotice>
      {orderedSteps.map((step) => (
        <View key={`${title}-${previewWidth}-${step.key}`} style={[styles.preview, { width: previewWidth }]}>
          <View style={styles.previewMeta}>
            <Text style={styles.previewName}>{String(steps.findIndex((item) => item.key === step.key) + 1).padStart(2, "0")}. {step.label}</Text>
            <Text style={styles.previewWidth}>{previewWidth} pt</Text>
          </View>
          <View style={styles.devicePreview}>{renderStep(step.key)}</View>
        </View>
      ))}
    </>
  );
}

export function OnboardingStoryboardGallery() {
  return (
    <StoryboardGallery
      accessibilityLabel="Formatos del onboarding"
      detail="Storyboard visual · sin sesión, API ni persistencia"
      notice="Cada formato presenta el flujo completo en orden, con datos fijos y sin persistencia."
      renderStep={(step) => step === "plans"
        ? <SubscriptionPreviewContent context="onboarding" topInsetReduction={topInsetReductionForOnboardingStoryboard(step)} />
        : <OnboardingJourneyView fullWidthExplanationTransition step={step} storyboardExplanationPresentation topInsetReduction={topInsetReductionForOnboardingStoryboard(step)} />}
      steps={onboardingJourneySteps}
      title="Flujo inicial"
    />
  );
}

export function LabelCaptureStoryboardGallery() {
  return (
    <StoryboardGallery
      accessibilityLabel="Formatos de la digitalización de etiquetas"
      detail="Storyboard visual · datos fijos, sin cámara, créditos ni persistencia"
      featuredStep="review"
      notice="Prueba primero la revisión: reduce la foto a media altura, desplázala verticalmente y recorre el formulario por separado. Debajo está el recorrido completo con datos de ejemplo."
      renderStep={(step) => <LabelCaptureStoryboardView step={step} />}
      steps={labelCaptureStoryboardSteps}
      title="Digitalización de etiquetas"
    />
  );
}

const styles = StyleSheet.create({
  preview: { alignSelf: "center", gap: tokens.spacing.sm, maxWidth: "100%" },
  previewMeta: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", paddingHorizontal: tokens.spacing.sm },
  previewName: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  previewWidth: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"] },
  devicePreview: { alignSelf: "center", backgroundColor: tokens.color.surfacePage, borderColor: tokens.color.borderStrong, borderRadius: 30, borderWidth: 1, maxWidth: "100%", overflow: "hidden", width: "100%" },
});
