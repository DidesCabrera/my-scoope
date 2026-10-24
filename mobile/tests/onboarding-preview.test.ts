import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string): Promise<string> {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("login renders the first storyboard view with the real authentication action", async () => {
  const login = await source("src/app/login.tsx");

  assert.ok(login.includes("OnboardingJourneyView"));
  assert.ok((await source("src/components/onboarding/onboarding-journey-view.tsx")).includes('loginDescription: { color: tokens.color.textMain'));
  assert.ok(login.includes('step="login"'));
  assert.ok(login.includes("startSignIn(returnHref)"));
});

test("staff can traverse a side-effect-free onboarding preview", async () => {
  const [preview, navigation] = await Promise.all([
    source("src/app/onboarding-preview.tsx"),
    source("src/components/navigation/app-navigation.tsx"),
  ]);

  assert.ok(navigation.includes("session?.is_staff"));
  assert.ok(navigation.includes("Vista previa del onboarding"));
  assert.ok(preview.includes('if (!session.is_staff) return <Redirect href="/account"'));
  assert.ok(preview.includes("gestureEnabled: false"));
  assert.ok(preview.includes("headerShown: false"));
  assert.ok(preview.includes("const headerCompensationTop = stepIndex >= 6 ? 88 : 0"));
  assert.ok(preview.includes("paddingTop: headerCompensationTop"));
  assert.equal(preview.includes("<Screen key={step}"), false);
  assert.ok(preview.includes("onboardingJourneySteps.length - 1"));
  assert.ok(preview.includes("presentationPropsForOnboardingStep"));
  assert.ok(preview.includes("{...presentationProps}"));
  const journey = await source("src/components/onboarding/onboarding-journey-view.tsx");
  assert.ok(journey.includes('require("../../../assets/images/login-background.jpg")'));
  assert.ok(journey.includes('title="Bienvenido a My Scoope!"'));
  assert.ok(journey.includes("isExplanation && styles.explanationDescription"));
  assert.ok(journey.includes("<MyScoopeBrandLogo scale={0.8} />"));
  assert.ok(journey.includes("explanationLogo: { marginBottom: -20 }"));
  assert.ok(journey.includes("styles.interactiveExplanationScreenFlush"));
  assert.ok(journey.includes("interactiveExplanationScreenFlush: { paddingTop: 76 }"));
  assert.ok(journey.includes("paddingTop: tokens.spacing.xxl - 18"));
  assert.ok(journey.includes('explanationSlide: { flex: 1, gap: tokens.spacing.lg, justifyContent: "center"'));
  assert.ok(journey.includes("contentContainerStyle={styles.explanationScrollContent}"));
  assert.ok(journey.includes("explanationScrollContent: { flexGrow: 1 }"));
  assert.ok(journey.includes("isExplanation && { marginBottom: (usesCenteredTitleSpacing ? tokens.spacing.sm : 0) + 10 }"));
  assert.ok(journey.includes("Nos alegra tenerte por aquí"));
  assert.ok(journey.includes("Queremos ayudarte a cumplir a conseguir los resultados que desees, apoyándote en el camino"));
  assert.ok(!journey.includes("onboarding-mind-to-body"));
  for (const emphasizedCopy of ["resultado de pequeñas buenas decisiones que tomes día a día", "de forma consistente", "te sentirás orgulloso de ti mismo", "se reflejará en un cambio físico y mental"]) {
    assert.ok(journey.includes(`<Text style={styles.descriptionEmphasis}>${emphasizedCopy}</Text>`));
  }
  assert.ok(journey.includes("Te deseamos lo mejor en este camino,"));
  assert.ok(journey.includes("Éxito!"));
  assert.ok(journey.includes('title="Que es My Scoope"'));
  assert.ok(!journey.includes("levels.map((level, levelIndex)"));
  assert.ok(!journey.includes("levelIndex < levels.length"));
  for (const emphasizedCopy of ["entorno nutricional", "Tus Librerías", "Alimentos, Comidas, Minutas diarias, y Programas Semanales"]) {
    assert.ok(journey.includes(`<Text style={styles.descriptionEmphasis}>${emphasizedCopy}</Text>`));
  }
  assert.ok(journey.includes("Podrás organizar tu alimentación en"));
  for (const entity of ["food", "meal", "dailyPlan", "program"]) {
    assert.ok(journey.includes(`entity: "${entity}"`));
  }
  assert.ok(journey.includes(`<EntityIcon entity={level.entity} size="hero" />`));
  for (const copy of ["La base nutricional del sistema", "Tu combinación de alimentos y porciones", "Tu distribución de comidas en el día", "Programas semanales", "Tu asignación de minutas en semanas"]) {
    assert.ok(journey.includes(copy));
  }
  assert.ok(journey.includes('levelDetail: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 18 }'));
  assert.ok(journey.includes("borderTopColor: tokens.color[level.entity]"));
  assert.ok(journey.includes("borderTopWidth: 3"));
  assert.ok(journey.includes('title="Forma tu propio criterio"'));
  assert.ok(journey.includes("titleTopSpacingReduction={12}"));
  assert.ok(!journey.includes("También dispusimos para ti"));
  assert.ok(journey.includes('panelsViewContent: { gap: tokens.spacing.lg, transform: [{ translateY: 20 }] }'));
  assert.ok(journey.includes('levels: { gap: tokens.spacing.sm, marginTop: 8 }'));
  assert.ok(journey.includes('executionPreview: { gap: tokens.spacing.lg, marginTop: 8 }'));
  assert.ok(journey.includes('style={styles.explanationVisualSpacing}'));
  for (const emphasizedCopy of ["instancias de aprendizaje y análisis", "paneles", "comparaciones"]) {
    assert.ok(journey.includes(`<Text style={styles.descriptionEmphasis}>${emphasizedCopy}</Text>`));
  }
  assert.ok(journey.includes("Te ofrecemos"));
  assert.ok(journey.includes("y comprende de mejor manera el impacto real"));
  assert.ok(journey.includes('<NutritionEntityCard'));
  const panelsView = journey.match(/function PanelsView[\s\S]*?function ControlView/)?.[0] ?? "";
  assert.ok(!panelsView.includes("indicators="));
  assert.ok(journey.includes('const referenceWeightKg = 80'));
  assert.ok(journey.includes('quantity: 200'));
  assert.ok(journey.includes('quantity: 120'));
  assert.ok(journey.includes('quantity: 60'));
  assert.ok(journey.includes('perKilogram: 39.36 / referenceWeightKg'));
  assert.ok(journey.includes('proteinPerKilogram: 32.76 / referenceWeightKg'));
  assert.ok(journey.includes('entity="meal"'));
  assert.ok(journey.includes('title="Comida equilibrada"'));
  assert.ok(journey.includes('<FoodPanels items={foods} showEditTab={false} />'));
  for (const food of ["Arroz cocido", "Pollo asado", "Palta"]) {
    assert.ok(journey.includes(`name: "${food}"`));
  }
  assert.ok(journey.includes('title="Ejecuta lo planeado"'));
  assert.ok(journey.includes('<MealCompletionToggleCard'));
  assert.ok(journey.includes('<MealCompletionToggleCard completed onToggle={() => undefined} />'));
  assert.ok(journey.includes('planLabel="Minutas diarias recorridas"'));
  assert.ok(journey.includes('mealLabel="Comidas Cumplidas"'));
  assert.ok(!journey.includes('title="1. Conversa"'));
  assert.ok(journey.includes("Puedes <Text style={styles.descriptionEmphasis}>llevar Minutas y Programas al Calendario</Text>, y activar el"));
  assert.ok(journey.includes("<Text style={styles.descriptionEmphasis}>registro de cumplimiento de comidas</Text>"));
  assert.ok(journey.includes("permitiéndote ver tu progreso"));
  assert.ok(journey.includes('title="Recibe Asistencia AI"'));
  assert.ok(journey.includes("Si necesitas ayuda en la construcción de programas de alimentación puedes recibirla"));
  assert.ok(journey.includes('titleAccessory={<View style={styles.assistanceIcon}><AssistantGradientIcon size={52} strokeWidth={1.8} /></View>}'));
  for (const emphasizedCopy of ["no debes frustrarte", "asistente nutricional", "propuestas", "aprobación para su aplicación"]) {
    assert.ok(journey.includes(`<Text style={styles.descriptionEmphasis}>${emphasizedCopy}</Text>`));
  }
  assert.ok(journey.includes("Nada ocurrirá si tu no lo apruebas"));
  assert.ok(journey.includes('<CreditDashboardGrid availableCredits={150} planName="Basic" style={styles.assistanceDashboardSpacing} />'));
  assert.ok(journey.includes('assistanceDashboardSpacing: { marginBottom: 8, marginTop: 8 }'));
  assert.ok(journey.includes("La asistencia funciona mediante un"));
  assert.ok(journey.includes('<Text style={styles.descriptionEmphasis}>sistema de créditos</Text>'));
  assert.ok(journey.includes('<Text style={styles.descriptionEmphasis}>No tener créditos jamás limitará la gestión sobre tu librería.</Text>'));
  assert.ok(journey.includes("styles.assistanceCreditDescription"));
  assert.ok(journey.includes('<ResponsibleUsePolicyLink label="Leer política de privacidad" onPress={noop} />'));
  assert.ok(journey.includes('<ResponsibleUsePolicyLink label="Leer términos de uso" onPress={noop} />'));
  assert.ok(journey.includes('<ResponsibleUsePolicyLink label="Leer política de reembolsos" onPress={noop} />'));
  assert.ok(journey.includes('index={13} showProgress={false} title="Tu primera minuta diaria"'));
  assert.ok(journey.includes('<ProposalDailyPlanCard dailyplan={controller.proposal.dailyplan} showNutrition={false} />'));
  assert.ok(!preview.includes("apiRequest"));
  assert.ok(!preview.includes("/api/v1/"));
});
