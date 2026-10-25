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
  const [preview, navigation, onboarding] = await Promise.all([
    source("src/app/onboarding-preview.tsx"),
    source("src/components/navigation/app-navigation.tsx"),
    source("src/app/onboarding.tsx"),
  ]);

  assert.ok(navigation.includes("session?.is_staff"));
  assert.ok(navigation.includes("Vista previa del onboarding"));
  assert.ok(preview.includes('if (!session.is_staff) return <Redirect href="/account"'));
  assert.ok(preview.includes("gestureEnabled: false"));
  assert.ok(preview.includes("headerShown: false"));
  assert.ok(preview.includes("const headerCompensationTop = stepIndex >= 8 ? 88 : 0"));
  assert.ok(preview.includes("paddingTop: headerCompensationTop"));
  assert.equal(preview.includes("<Screen key={step}"), false);
  assert.ok(preview.includes("onboardingJourneySteps.length - 1"));
  assert.ok(preview.includes("presentationPropsForOnboardingStep"));
  assert.ok(preview.includes("{...presentationProps}"));
  const journey = await source("src/components/onboarding/onboarding-journey-view.tsx");
  assert.ok(journey.indexOf('key: "control"') < journey.indexOf('key: "panels"'));
  assert.ok(onboarding.includes('const introSteps: OnboardingJourneyStep[] = ["value", "structure", "control", "panels", "panelsCopy", "compareShare", "progress"]'));
  assert.ok(journey.indexOf('key: "panelsCopy"') < journey.indexOf('key: "compareShare"'));
  assert.ok(journey.indexOf('key: "compareShare"') < journey.indexOf('key: "progress"'));
  assert.ok(journey.includes('const explanationSteps = onboardingJourneySteps.slice(1, 8)'));
  assert.ok(journey.includes('const interactiveExplanation = Boolean(controller) && index >= 1 && index <= 7'));
  assert.ok(journey.includes('ExplanationDots action={index === 7 ? <ContinueChip /> : undefined}'));
  assert.ok(journey.includes('require("../../../assets/images/login-background.jpg")'));
  assert.ok(journey.includes('title="No improvises,"'));
  assert.ok(journey.includes('styles.loginTitleChip, styles.valueTitleChip'));
  assert.ok(journey.includes('titleStyle={styles.valueTitleText}'));
  assert.ok(journey.includes('valueTitleText: { fontSize: 37, lineHeight: 43, marginTop: 96 }'));
  assert.ok(journey.includes('valueTitleChipText: { fontSize: 52, lineHeight: 61 }'));
  assert.ok(journey.includes('valueTitleChip: { marginBottom: 48, marginTop: -10 }'));
  assert.ok(journey.includes('>Planifica</Text>'));
  assert.ok(journey.includes('My Scoope no es un contador de calorías,{"\\n"}es un planificador de alimentación</Text>'));
  assert.ok(journey.includes('Arma minutas con tus comidas, calendarízalas y sigue tu programación"'));
  assert.ok(journey.includes('valueDescription: { fontSize: 18, lineHeight: 26 }'));
  assert.ok(journey.includes('valueDescriptionEmphasis: { fontWeight: tokens.weight.bold }'));
  assert.ok(journey.includes("isExplanation && styles.explanationDescription"));
  assert.ok(journey.includes("<MyScoopeBrandLogo scale={0.88} />"));
  assert.ok(journey.includes("explanationLogo: { marginBottom: -20 }"));
  assert.ok(journey.includes("styles.interactiveExplanationScreenFlush"));
  assert.ok(journey.includes("interactiveExplanationScreenFlush: { paddingTop: 76 }"));
  assert.ok(journey.includes('explanationSlide: { flex: 1, gap: tokens.spacing.lg, justifyContent: "flex-start", paddingTop: 40 }'));
  assert.ok(journey.includes('pageStep.key === "panels" && styles.ppkExplanationSlide'));
  assert.ok(journey.includes('pageStep.key === "panelsCopy" && styles.commitmentsExplanationSlide'));
  assert.ok(journey.includes('ppkExplanationSlide: { paddingTop: 20 }'));
  assert.ok(journey.includes('commitmentsExplanationSlide: { paddingTop: 8 }'));
  assert.ok(journey.includes("contentContainerStyle={styles.explanationScrollContent}"));
  assert.ok(journey.includes("explanationScrollContent: { flexGrow: 1 }"));
  assert.ok(journey.includes("isExplanation && { marginBottom: (usesCenteredTitleSpacing ? tokens.spacing.sm : 0) + 10 }"));
  assert.ok(!journey.includes("onboarding-mind-to-body"));
  assert.ok(!journey.includes("Nos alegra tenerte por aquí"));
  assert.ok(journey.includes('title="Reúne tus comidas recurrentes"'));
  assert.ok(journey.includes('const continueFooterBottomMargin = 49;'));
  assert.ok(journey.includes('fixedProfileFooterBottomSpacing: index >= 9 && index <= 14 ? continueFooterBottomMargin : 0'));
  assert.ok(journey.includes('explanationFooter: { alignItems: "center", gap: tokens.spacing.md, marginBottom: continueFooterBottomMargin'));
  assert.ok(journey.includes('explanationFooterCompact: { marginTop: -16 }'));
  assert.ok(journey.includes('icon={LibraryBig}'));
  assert.ok(journey.includes('showIconAboveTitle'));
  assert.ok(journey.includes('isExplanation && showIconAboveTitle && styles.explanationIconTitleSpacing'));
  assert.ok(journey.includes('explanationIconTitleSpacing: { marginTop: 2 }'));
  assert.ok(journey.includes('structureRaisedContent: { gap: tokens.spacing.lg }'));
  assert.ok(!journey.includes('structureRaisedContent: { gap: tokens.spacing.lg, transform:'));
  assert.ok(journey.includes('levelRowFrame: { borderRadius: tokens.radius.panel, marginHorizontal: tokens.spacing.md, overflow: "hidden" }'));
  assert.ok(journey.includes('borderTopLeftRadius: tokens.radius.panel - 3, borderTopRightRadius: tokens.radius.panel - 3'));
  assert.ok(journey.includes('sectionTitle: "y arma opciones de minutas"'));
  assert.ok(journey.includes('structureClosingText: { color: tokens.color.textMain, marginTop: 40 - tokens.spacing.md }'));
  assert.ok(journey.includes('styles.structureClosingText, styles.structureViewClosingText]}>Y luego puedes ajustar tus porciones según tu objetivo nutricional</Text>'));
  assert.ok(journey.includes('structureLevels: { marginTop: -14 }'));
  assert.ok(journey.includes('structureViewClosingText: { marginTop: tokens.spacing.md + 10 }'));
  assert.ok(journey.includes('panelsViewClosingText: { marginTop: tokens.spacing.sm + 10 }'));
  assert.ok(journey.includes('assistanceClosingText: { marginTop: -10 }'));
  assert.ok(!journey.includes("levels.map((level, levelIndex)"));
  assert.ok(!journey.includes("levelIndex < levels.length"));
  const structureView = journey.match(/function StructureView[\s\S]*?function PanelsView/)?.[0] ?? "";
  for (const entity of ["meal", "dailyPlan"]) {
    assert.ok(structureView.includes(`entity: "${entity}"`));
  }
  for (const entity of ["food", "program"]) {
    assert.ok(!structureView.includes(`entity: "${entity}"`));
  }
  assert.ok(journey.includes(`<EntityIcon entity={level.entity} size="hero" />`));
  for (const label of ["Mis Comidas", "Mis Minutas"]) {
    assert.ok(structureView.includes(`label: "${label}"`));
  }
  assert.ok(structureView.includes('<EntityIcon entity={level.entity} size="hero" />'));
  assert.ok(structureView.includes('<Text style={styles.levelTitle}>{level.label}</Text>'));
  assert.ok(structureView.includes('<Text style={styles.levelDetail}>{level.detail}</Text>'));
  assert.ok(structureView.includes('detail: "Compuesto por alimentos"'));
  assert.ok(structureView.includes('detail: "Compuesto por comidas"'));
  assert.ok(structureView.includes('mealFoodIcons.map((FoodIcon, iconIndex) => ('));
  assert.ok(journey.includes('const mealFoodIcons = [Apple, Carrot, Beef, Fish]'));
  assert.ok(structureView.includes('level.entity === "dailyPlan" ? ('));
  assert.ok(structureView.includes('accessibilityLabel="Cuatro comidas" style={styles.entityContentsGrid}'));
  assert.ok(structureView.includes('backgroundColor: tokens.color.meal'));
  assert.ok(structureView.includes('<Utensils color={tokens.color.entityIconForeground} size={13} strokeWidth={2} />'));
  assert.ok(journey.includes('levelCopy: { flex: 1, gap: 2, minWidth: 0 }'));
  assert.ok(journey.includes('levelTitle: { color: tokens.color.textMain, fontSize: 20'));
  assert.ok(journey.includes('<TopAccentCard accent={tokens.color[level.entity]}>'));
  assert.ok(journey.includes('levels: { gap: tokens.spacing.xl + 16, marginTop: -tokens.spacing.sm }'));
  const panelsView = journey.match(/function PanelsView[\s\S]*?function ControlView/)?.[0] ?? "";
  assert.ok(panelsView.includes('title={"Proteínas por kilo\\nde peso - PPK"}'));
  assert.ok(panelsView.includes('titleStyle={styles.panelsTitle}'));
  assert.ok(panelsView.includes('styles.panelsViewContent'));
  assert.ok(journey.includes('panelsViewContent: { gap: 20 }'));
  assert.ok(!journey.includes('panelsViewContent: { gap: 20, transform:'));
  assert.ok(journey.includes('panelsTitle: { marginBottom: 0 }'));
  assert.ok(panelsView.includes('% Calorías por{"\\n"}macros - Alloc'));
  assert.ok(panelsView.includes('showIconAboveTitle'));
  assert.ok(panelsView.includes('styles.structureSection'));
  assert.ok(panelsView.includes('<Text style={styles.levelTitle}>PPK</Text>'));
  assert.ok(panelsView.includes('Gramos de proteína por kilo de peso corporal'));
  assert.ok(panelsView.includes('<ProteinPerKilogramBadge style={styles.panelsPpkBadge} textSize={17} value={2} />'));
  assert.ok(journey.includes('panelsPpkBadge: { borderRadius: 10, minHeight: 29, paddingHorizontal: 10 }'));
  assert.ok(journey.includes('panelsAllocationPreview: { gap: 10, width: 100 }'));
  assert.ok(panelsView.includes('<Text style={styles.levelTitle}>Alloc</Text>'));
  assert.ok(panelsView.includes('Distribución de calorías por macronutriente'));
  assert.ok(!panelsView.includes('styles.panelsMetricIcon'));
  assert.ok(panelsView.includes('<KpiAllocationBar tone="protein" value={33} />'));
  assert.ok(panelsView.includes('<KpiAllocationBar tone="carbs" value={41} />'));
  assert.ok(panelsView.includes('<KpiAllocationBar tone="fat" value={26} />'));
  assert.ok(panelsView.includes('styles.structureClosingText, styles.panelsViewClosingText]}>También verás las calorías y gramos por macros correspondientes</Text>'));
  assert.ok(panelsView.includes('<TopAccentCard accent={tokens.color.protein} style={styles.panelsAllocationRow}>'));
  const commitmentsView = journey.match(/function PanelsCopyView[\s\S]*?function CompareShareView/)?.[0] ?? "";
  assert.ok(commitmentsView.includes('icon={Pin}'));
  assert.ok(commitmentsView.includes('title={"Mejora tu planificación\\ncon compromisos"}'));
  assert.ok(commitmentsView.includes('styles.commitmentCards'));
  assert.ok(commitmentsView.includes('commitmentKinds.map((kind) =>'));
  assert.ok(commitmentsView.includes('commitmentPresentation[kind]'));
  assert.ok(commitmentsView.includes('commitmentDetails[kind]'));
  for (const subtitle of ["Genera tu lista de compra", "Define tus preparaciones", "Diseña tus minutas según tu entrenamiento", "Chequea tu progreso con un profesional"]) {
    assert.ok(commitmentsView.includes(subtitle));
  }
  assert.ok(commitmentsView.includes('<TopAccentCard accent={color} key={kind} style={styles.commitmentCard}>'));
  assert.ok(!commitmentsView.includes('<Text style={styles.levelTitle}>PPK</Text>'));
  assert.ok(!commitmentsView.includes('% Calorías por{"\\n"}macros - Alloc'));
  assert.ok(commitmentsView.includes('Calendarízalos para tener una visión más completa</Text>'));
  const compareShareView = journey.match(/function CompareShareView[\s\S]*?function ControlView/)?.[0] ?? "";
  assert.ok(compareShareView.includes('title="Compara tus alimentos, comidas y minutas"'));
  assert.ok(compareShareView.includes('Comparte tus librerías{"\\n"}con amigos'));
  assert.ok(compareShareView.includes('<View style={styles.sharingSectionHeading}>'));
  assert.ok(compareShareView.includes('icon={Scale}'));
  assert.ok(compareShareView.indexOf('<Send color={tokens.color.textMain} size={27} strokeWidth={1.8} />') < compareShareView.indexOf('Comparte tus librerías{"\\n"}con amigos'));
  assert.ok(compareShareView.includes('<View style={styles.sharingHeroIcon}>'));
  assert.ok(compareShareView.includes('<TopAccentCard accent={tokens.color.food}>'));
  assert.ok(compareShareView.includes('<EntityIcon backgroundColor={tokens.color.food} entity="comparison" size="hero" />'));
  assert.ok(compareShareView.includes('<TopAccentCard accent={tokens.color.meal}>'));
  assert.ok(compareShareView.includes('<ExplanationDots index={index} />'));
  assert.ok(journey.includes('panelsAllocationRow: { alignItems: "flex-start", columnGap: 20 }'));
  const controlView = journey.match(/function ControlView[\s\S]*?function ProgressView/)?.[0] ?? "";
  assert.ok(controlView.includes('title="Asigna minutas a tu calendario"'));
  assert.ok(controlView.includes('icon={CalendarDays}'));
  assert.ok(controlView.includes('showIconAboveTitle'));
  assert.ok(controlView.includes('entity: "dpm", label: "Mi calendario"'));
  assert.ok(controlView.includes('entity: "program", label: "Mis programas", sectionTitle: "O planifícalas en programas"'));
  assert.equal(controlView.match(/detail: "Compuesto por minutas"/g)?.length, 2);
  assert.ok(controlView.includes('<Text style={styles.levelDetail}>{level.detail}</Text>'));
  assert.ok((await source("src/components/ui/product.tsx")).includes('program: ChartNoAxesCombined'));
  assert.ok(controlView.includes('styles.structureRaisedContent'));
  assert.ok(controlView.includes('<TopAccentCard accent={level.entity === "dpm" ? `${tokens.color.dailyPlan}80` : tokens.color[level.entity]}>'));
  assert.ok(controlView.includes('backgroundColor={level.entity === "dpm" ? `${tokens.color.dailyPlan}80` : undefined}'));
  assert.ok(controlView.includes('accessibilityLabel="Cuatro minutas" style={styles.entityContentsGrid}'));
  assert.ok(controlView.includes('backgroundColor: tokens.color.dailyPlan'));
  assert.ok(controlView.includes('<ClipboardList color={tokens.color.entityIconForeground} size={13} strokeWidth={2} />'));
  assert.ok(controlView.includes('styles.structureClosingText, styles.structureViewClosingText]}>Y luego puedes calendarizar las minutas ya estructuradas</Text>'));
  assert.ok(!controlView.includes('<MealCompletionToggleCard'));
  assert.ok(!controlView.includes('<ProgramActiveKpis'));
  const progressView = journey.match(/function ProgressView[\s\S]*?function DisclosuresView/)?.[0] ?? "";
  assert.ok(progressView.includes('title="Ahorra tiempo con un asistente"'));
  assert.ok(progressView.includes('icon={Sparkles}'));
  assert.ok(progressView.includes('showIconAboveTitle'));
  assert.ok(progressView.includes('description={null}'));
  assert.ok(progressView.includes('<TopAccentCard accent={tokens.color.carbs}>'));
  assert.ok(progressView.includes('<AssistantGradientIcon size={40} strokeWidth={1.8} />'));
  assert.ok(!progressView.includes('onboarding-assistance-card-gradient'));
  assert.ok(progressView.includes('<Text style={styles.levelTitle}>Asistente nutricional</Text>'));
  assert.ok(progressView.includes('Realiza propuestas y ajuste'));
  assert.ok(progressView.indexOf('<TopAccentCard accent={tokens.color.carbs}>') < progressView.indexOf('styles.assistancePlansCard'));
  assert.ok(progressView.includes('(["Free", "Basic", "Pro"] as const).map'));
  assert.ok(progressView.includes('Las tareas ocupan créditos según su dificultad'));
  assert.ok(progressView.includes('<Text style={styles.structureSectionTitle}>Pide propuestas según{"\\n"}tus objetivos</Text>'));
  assert.ok(progressView.includes('Puedes pedir diferentes tareas, como construir programas semanales, ajustar minutas, comparar alimentos, registrar comidas, entre otros\n'));
  assert.ok(progressView.indexOf('<TopAccentCard accent={tokens.color.carbs}>') < progressView.indexOf('Pide propuestas según'));
  assert.ok(progressView.indexOf('Pide propuestas según') < progressView.indexOf('styles.assistancePlansCard'));
  assert.ok(journey.includes('<ResponsibleUsePolicyLink label="Leer política de privacidad" onPress={noop} />'));
  assert.ok(journey.includes('<ResponsibleUsePolicyLink label="Leer términos de uso" onPress={noop} />'));
  assert.ok(journey.includes('<ResponsibleUsePolicyLink label="Leer política de reembolsos" onPress={noop} />'));
  assert.ok(journey.includes('{index === 8 ? <View style={styles.disclosuresConfirmationSpacing}><ResponsibleUseConfirmationNotice /></View> : null}'));
  const disclosuresView = journey.match(/function DisclosuresView[\s\S]*?function GoalView/)?.[0] ?? "";
  assert.equal(disclosuresView.includes("Al continuar confirmas"), false);
  assert.ok(journey.includes('index={14} showProgress={false} title="Tu primera minuta diaria"'));
  assert.ok(journey.includes('<ProposalDailyPlanCard dailyplan={controller.proposal.dailyplan} showNutrition={false} />'));
  assert.ok(!preview.includes("apiRequest"));
  assert.ok(!preview.includes("/api/v1/"));
});
