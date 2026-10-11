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
  assert.ok(preview.includes("<Screen key={step}"));
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
  assert.ok(journey.includes("isExplanation && { marginBottom: (usesCenteredTitleSpacing ? tokens.spacing.sm : 0) + 10 }"));
  assert.ok(journey.includes("Antes que todo, queremos declarar con toda honestidad"));
  assert.ok(journey.includes("Te deseamos lo mejor en este camino, éxito!"));
  assert.ok(journey.includes('title="Que es My Scoope"'));
  for (const emphasizedCopy of ["entorno nutricional", "Alimentos", "Comidas", "Planes Diarios", "Programas Semanales"]) {
    assert.ok(journey.includes(`<Text style={styles.descriptionEmphasis}>${emphasizedCopy}</Text>`));
  }
  assert.ok(journey.includes("La planificación la realiza"));
  assert.ok(journey.includes('title="Forma tu propio criterio"'));
  for (const emphasizedCopy of ["instancias de aprendizaje y análisis", "paneles", "comparaciones", "fundamentos nutricionales"]) {
    assert.ok(journey.includes(`<Text style={styles.descriptionEmphasis}>${emphasizedCopy}</Text>`));
  }
  assert.ok(journey.includes('title="Ejecuta lo planeado"'));
  for (const emphasizedCopy of ["registro de cumplimientos de las comidas", "bitácora de aprendizaje"]) {
    assert.ok(journey.includes(`<Text style={styles.descriptionEmphasis}>${emphasizedCopy}</Text>`));
  }
  assert.ok(journey.includes('title="Recibe Asistencia AI"'));
  for (const emphasizedCopy of ["no debes frustrarte", "asistente nutricional", "propuestas", "aprobación para su aplicación"]) {
    assert.ok(journey.includes(`<Text style={styles.descriptionEmphasis}>${emphasizedCopy}</Text>`));
  }
  assert.ok(journey.includes("Nada ocurrirá si tu no lo apruebas"));
  assert.ok(!preview.includes("apiRequest"));
  assert.ok(!preview.includes("/api/v1/"));
});
