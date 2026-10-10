import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { AssistantCreditBalance } from "@/components/assistant/assistant-credit-balance";
import { commercialPlanBenefits, SubscriptionPlanCard, SubscriptionPurchaseButton } from "@/components/subscriptions/subscription-plan-card";
import { AppHeader, Button, Card, DistributedTabBar, MyScoopeLogo, SectionTitle, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { subscriptionPlanAccent } from "@/presentation/subscription";

export type SubscriptionPreview = "onboarding" | "account";

const noop = () => undefined;

function PlanExamples() {
  return (
    <>
      <SubscriptionPlanCard accent={tokens.color.carbs} benefits={commercialPlanBenefits.Basic} name="Basic" price="$3.990/mes">
        <Text style={textStyles.caption}>Elige la modalidad de tu suscripción.</Text>
        <SubscriptionPurchaseButton label="Mensual · $3.990/mes" onPress={noop} />
        <SubscriptionPurchaseButton label="Anual · $39.900/año · Ahorra 17%" onPress={noop} />
      </SubscriptionPlanCard>
      <SubscriptionPlanCard accent={tokens.color.protein} benefits={commercialPlanBenefits.Pro} name="Pro" price="$6.990/mes">
        <Text style={textStyles.caption}>Elige la modalidad de tu suscripción.</Text>
        <SubscriptionPurchaseButton label="Mensual · $6.990/mes" onPress={noop} />
        <SubscriptionPurchaseButton label="Anual · $69.900/año · Ahorra 17%" onPress={noop} />
      </SubscriptionPlanCard>
    </>
  );
}

function SubscriptionInformationCard() {
  return (
    <Card style={styles.subscriptionInformationCard}>
      <SectionTitle title="Información de la suscripción" />
      <Text style={textStyles.muted}>El cobro se realiza a tu cuenta de App Store al confirmar. La suscripción se renueva automáticamente por el mismo periodo y precio vigente hasta que la canceles desde tu cuenta de Apple. Puedes cancelarla al menos 24 horas antes del término del periodo actual.</Text>
      <Text style={textStyles.caption}>La compra habilita las funciones y créditos incluidos en el plan seleccionado en todos tus dispositivos donde uses la misma cuenta de My Scoope.</Text>
      <Button label="Política de privacidad" onPress={noop} variant="secondary" />
      <Button label="Términos de uso" onPress={noop} variant="secondary" />
      <Button label="Cancelaciones y reembolsos" onPress={noop} variant="secondary" />
    </Card>
  );
}

export function SubscriptionPreviewContent({ context, topInsetReduction = 0 }: { context: SubscriptionPreview; topInsetReduction?: number }) {
  const isOnboarding = context === "onboarding";
  return (
    <View style={[styles.previewContent, topInsetReduction > 0 && { paddingTop: Math.max(0, tokens.spacing.screen - topInsetReduction) }]}>
        {isOnboarding ? (
          <View style={styles.onboardingIntro}>
            <View style={styles.onboardingLogo}><MyScoopeLogo /></View>
            <Text style={styles.onboardingTitle}>Elige un plan</Text>
            <Text style={styles.onboardingDescription}>Compara lo que incluyen Free, Basic y Pro.{"\n"}Puedes cambiar de plan más adelante.</Text>
          </View>
        ) : (
          <View style={styles.accountHeaderPreview}>
            <AppHeader alignment="center" title="Suscripciones y Bolsas" />
            <View style={styles.subscriptionDescriptionGroup}>
              <Text style={styles.subscriptionDescription}>Nuestras suscripciones te entregan beneficios para enriquecer tus librerías y facilitar tu gestión nutricional.</Text>
              <Text style={styles.subscriptionDescription}>Ademas si eres un usuario muy activo que necesita asistencia adicional, puedes comprar bolsas de créditos en el momento que lo desees.</Text>
            </View>
          </View>
        )}
        {!isOnboarding ? (
          <>
            <Card accent={subscriptionPlanAccent("Pro")}>
              <Text style={styles.eyebrow}>SUSCRIPCIÓN ACTUAL</Text>
              <Text style={styles.planName}>Pro</Text>
              <AssistantCreditBalance availability={{ available_credits: 1500 }} contained />
            </Card>
            <SectionTitle title="Suscripciones disponibles" titleStyle={styles.commercialSectionTitle} />
          </>
        ) : null}
        <SubscriptionPlanCard accent={tokens.color.fat} benefits={commercialPlanBenefits.Free} caption="Incluido sin costo." name="Free" price={isOnboarding ? "Gratis" : "$0/mes"}>
          {isOnboarding ? <SubscriptionPurchaseButton label="Continuar con Free" onPress={noop} /> : null}
        </SubscriptionPlanCard>
        <PlanExamples />
        <SubscriptionInformationCard />
    </View>
  );
}

export function SubscriptionGallery() {
  const [preview, setPreview] = useState<SubscriptionPreview>("onboarding");

  return (
    <View style={styles.gallery}>
      <SectionTitle detail="Previsualización estática · sin compras ni llamadas a la tienda" title="Suscripciones y Bolsas" />
      <DistributedTabBar<SubscriptionPreview>
        accessibilityLabel="Contexto de la vista de suscripciones"
        activeTab={preview}
        onChange={setPreview}
        tabs={[{ key: "onboarding", label: "Desde onboarding" }, { key: "account", label: "Desde Cuenta" }]}
      />
      <View style={styles.phonePreview}><SubscriptionPreviewContent context={preview} /></View>
    </View>
  );
}

const styles = StyleSheet.create({
  accountHeaderPreview: { paddingBottom: 20, paddingTop: 20 },
  commercialSectionTitle: { fontSize: tokens.type.section, lineHeight: 26 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1 },
  gallery: { gap: tokens.spacing.md },
  onboardingDescription: { color: tokens.color.textMuted, fontSize: 18, lineHeight: 25, textAlign: "center" },
  onboardingIntro: { alignItems: "center", gap: tokens.spacing.lg, paddingBottom: tokens.spacing.sm, paddingTop: tokens.spacing.lg },
  onboardingLogo: { marginBottom: tokens.spacing.lg },
  onboardingTitle: { color: tokens.color.textMain, fontSize: 34, fontWeight: tokens.weight.extraBold, lineHeight: 40, textAlign: "center" },
  phonePreview: { alignSelf: "center", gap: tokens.spacing.md, maxWidth: 414, width: "100%" },
  planName: { color: tokens.color.textMain, fontSize: 26, fontWeight: tokens.weight.extraBold },
  previewContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen },
  subscriptionInformationCard: { marginTop: tokens.spacing.lg },
  subscriptionDescription: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 24, textAlign: "center" },
  subscriptionDescriptionGroup: { gap: tokens.spacing.md, marginTop: tokens.spacing.lg },
});
