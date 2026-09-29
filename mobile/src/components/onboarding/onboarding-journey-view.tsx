import {
  Activity,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  BookOpen,
  BrainCircuit,
  Check,
  CircleUserRound,
  Dumbbell,
  Eye,
  Gauge,
  HeartPulse,
  Home,
  Layers3,
  LockKeyhole,
  Scale,
  Sparkles,
  Target,
} from "lucide-react-native";
import type { ComponentType, ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { EntityPanelTabs, PanelSurface } from "@/components/panels";
import { Brand, Button, Card, ChoiceRow, Field, InlineNotice, Pill, textStyles } from "@/components/ui";
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
  { key: "summary", shortLabel: "Resumen", label: "Resumen de la ficha" },
  { key: "plans", shortLabel: "Planes", label: "Planes disponibles" },
  { key: "home", shortLabel: "Inicio", label: "Primer plan diario" },
] as const;

export type OnboardingJourneyStep = (typeof onboardingJourneySteps)[number]["key"];

export const onboardingNutritionFields = ["goal", "birth_date", "sex", "height_cm", "weight_kg", "activity_level", "training_frequency"] as const;

type Icon = ComponentType<{ color?: string; size?: number; strokeWidth?: number }>;

const noop = () => undefined;

function StepHeader({ icon: IconComponent, index, eyebrow, title, description }: {
  description: string;
  eyebrow: string;
  icon: Icon;
  index: number;
  title: string;
}) {
  return (
    <View style={styles.intro}>
      <View style={styles.stepMeta}>
        <Text style={styles.stepCount}>{String(index + 1).padStart(2, "0")} / {onboardingJourneySteps.length}</Text>
        <View accessibilityLabel={`Paso ${index + 1} de ${onboardingJourneySteps.length}`} style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${((index + 1) / onboardingJourneySteps.length) * 100}%` }]} />
        </View>
      </View>
      <View style={styles.iconWell}><IconComponent color={tokens.color.entityIconForeground} size={27} strokeWidth={1.8} /></View>
      <Text style={styles.eyebrow}>{eyebrow}</Text>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.description}>{description}</Text>
    </View>
  );
}

function JourneyFooter({ index, primary = "Continuar", secondary = "Atrás" }: { index: number; primary?: string; secondary?: string }) {
  return (
    <View style={styles.footer}>
      <Button label={primary} onPress={noop} />
      {index > 0 ? (
        <Pressable accessibilityRole="button" onPress={noop} style={styles.backAction}>
          <ArrowLeft color={tokens.color.textMuted} size={16} />
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
  return (
    <>
      <Brand />
      <View accessibilityLabel={`Paso ${index + 1} de ${onboardingJourneySteps.length}`} style={styles.loginHero}>
        <Text style={styles.loginKicker}>ACCESO</Text>
        <Text style={styles.loginTitle}>Inicia sesión para guardar tu progreso</Text>
        <Text style={textStyles.muted}>Usa tu cuenta para continuar el proceso en cualquiera de tus dispositivos.</Text>
      </View>
      <Card accent={tokens.color.program}>
        <Text style={styles.cardTitle}>Accede a tu cuenta</Text>
        <Text style={textStyles.muted}>Inicia sesión o crea una cuenta para guardar tu progreso en todos tus dispositivos.</Text>
        <Button label="Iniciar sesión o crear cuenta" onPress={noop} />
      </Card>
      <Text style={styles.quietCenter}>Tu información quedará asociada a tu cuenta.</Text>
    </>
  );
}

function ValueView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="My Scoope organiza tu objetivo, calcula referencias nutricionales y las convierte en un plan diario que puedes revisar." eyebrow="Funciones principales" icon={Target} index={index} title="Qué puedes hacer con My Scoope" />
      <Card accent={tokens.color.dailyPlan}>
        <ExplanationCard body="Una estructura diaria que puedes revisar, adaptar y ejecutar." icon={Check} title="Plan diario" />
        <ExplanationCard body="Calorías, macros y cantidades en una lectura ordenada." icon={Gauge} title="Referencias nutricionales" />
      </Card>
      <JourneyFooter index={index} />
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
      <JourneyFooter index={index} />
    </>
  );
}

function PanelsView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="Cada panel muestra primero un resumen y permite consultar calorías, macronutrientes y detalle." eyebrow="Paneles de información" icon={Eye} index={index} title="Cómo leer los paneles" />
      <Card accent={tokens.color.interactivePrimary}>
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
      <JourneyFooter index={index} />
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
      <JourneyFooter index={index} />
    </>
  );
}

function ProgressView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="Compara lo planificado con tus registros para decidir si necesitas ajustar el plan." eyebrow="Seguimiento" icon={BarChart3} index={index} title="Cómo revisar tu progreso" />
      <Card accent={tokens.color.success}>
        <View style={styles.metricRow}><Text style={styles.metricLabel}>Adherencia semanal</Text><Text style={styles.metricValue}>86%</Text></View>
        <View style={styles.metricTrack}><View style={styles.metricFill} /></View>
        <View style={styles.progressFacts}>
          <ExplanationCard body="Registro simple y cronológico." icon={Scale} title="Peso" />
          <ExplanationCard body="Revisiones que explican cambios." icon={Activity} title="Evolución" />
        </View>
      </Card>
      <JourneyFooter index={index} />
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
  return (
    <>
      <StepHeader description="Tu objetivo orienta el ajuste energético y la referencia inicial de proteína. Siempre podrás cambiarlo." eyebrow="Objetivo nutricional" icon={Target} index={index} title="Define tu objetivo" />
      <View style={styles.optionGrid}>
        {["Bajar grasa", "Ganar masa muscular", "Mantenerme", "Rendimiento deportivo", "Comer mejor"].map((label, optionIndex) => (
          <View key={label} style={[styles.optionCard, optionIndex === 0 && styles.optionCardSelected]}>
            <Text style={[styles.optionText, optionIndex === 0 && styles.optionTextSelected]}>{label}</Text>
            {optionIndex === 0 ? <Check color={tokens.color.surfaceApp} size={17} /> : null}
          </View>
        ))}
      </View>
      <JourneyFooter index={index} />
    </>
  );
}

function IdentityView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="La edad y el sexo usado para el cálculo forman parte de la estimación de tu gasto basal." eyebrow="Datos para el cálculo" icon={CircleUserRound} index={index} title="Ingresa tus datos personales" />
      <Card accent={tokens.color.dailyPlan}>
        <Field label="Fecha de nacimiento" onChangeText={noop} placeholder="AAAA-MM-DD" value="1990-05-10" />
        <ChoiceRow label="Sexo usado para el cálculo nutricional" onChange={noop} options={[{ value: "male", label: "Masculino" }, { value: "female", label: "Femenino" }]} value="male" />
      </Card>
      <InlineNotice>Usamos estos datos para estimaciones nutricionales, no para definir tu identidad.</InlineNotice>
      <JourneyFooter index={index} />
    </>
  );
}

function MeasurementsView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="La altura y el peso permiten estimar tu gasto energético y calcular referencias por kilogramo." eyebrow="Datos para el cálculo" icon={Scale} index={index} title="Ingresa tus medidas actuales" />
      <Card accent={tokens.color.dailyPlan}>
        <View style={styles.measurementFields}>
          <View style={styles.flex}><Field keyboardType="number-pad" label="Altura (cm)" onChangeText={noop} placeholder="178" value="178" /></View>
          <View style={styles.flex}><Field keyboardType="decimal-pad" label="Peso (kg)" onChangeText={noop} placeholder="82,5" value="82,5" /></View>
        </View>
        <Text style={textStyles.caption}>El peso inicial quedará como primera referencia de tu evolución.</Text>
      </Card>
      <JourneyFooter index={index} />
    </>
  );
}

function ActivityView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="Separa el movimiento habitual de los entrenamientos para evitar contarlos dos veces." eyebrow="Datos para el cálculo" icon={Dumbbell} index={index} title="Describe tu actividad y entrenamiento" />
      <View accessibilityLabel={`Datos solicitados: ${onboardingNutritionFields.join(", ")}`}>
        <Card accent={tokens.color.program}>
          <Text style={styles.fieldLabel}>Actividad habitual</Text>
          <View style={styles.activityList}>
            {[
              ["Sedentaria", "La mayor parte del día sentado"],
              ["Ligera", "Caminatas y movimiento ocasional"],
              ["Moderada", "Movimiento frecuente durante la semana"],
            ].map(([label, detail], optionIndex) => (
              <View key={label} style={[styles.activityOption, optionIndex === 1 && styles.activityOptionSelected]}>
                <View style={styles.flex}><Text style={styles.activityLabel}>{label}</Text><Text style={styles.activityDetail}>{detail}</Text></View>
                <View style={[styles.radio, optionIndex === 1 && styles.radioSelected]}>{optionIndex === 1 ? <View style={styles.radioDot} /> : null}</View>
              </View>
            ))}
          </View>
          <ChoiceRow label="Entrenamientos por semana" onChange={noop} options={["0–1", "2–3", "4–5", "6+"].map((label) => ({ value: label, label }))} value="2–3" />
        </Card>
      </View>
      <JourneyFooter index={index} />
    </>
  );
}

function SummaryView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="Comprueba los datos y la estimación inicial antes de continuar." eyebrow="Resumen de la ficha" icon={Gauge} index={index} title="Revisa tu información" />
      <Card accent={tokens.color.dailyPlan}>
        <View style={styles.summaryHero}><Text style={styles.summaryValue}>2.340</Text><Text style={styles.summaryUnit}>kcal de mantenimiento estimado</Text></View>
        <View style={styles.summaryGrid}>
          <View style={styles.summaryCell}><Text style={styles.summaryLabel}>Objetivo</Text><Text style={styles.summaryText}>Bajar grasa</Text></View>
          <View style={styles.summaryCell}><Text style={styles.summaryLabel}>Referencia</Text><Text style={styles.summaryText}>82,5 kg</Text></View>
          <View style={styles.summaryCell}><Text style={styles.summaryLabel}>Actividad</Text><Text style={styles.summaryText}>Ligera</Text></View>
          <View style={styles.summaryCell}><Text style={styles.summaryLabel}>Entrenamiento</Text><Text style={styles.summaryText}>2–3 días</Text></View>
        </View>
      </Card>
      <InlineNotice>El mantenimiento usa edad, sexo de cálculo, altura, peso y actividad. La frecuencia de entrenamiento se conserva como contexto mientras afinamos su uso.</InlineNotice>
      <JourneyFooter index={index} primary="Confirmar mi punto de partida" />
    </>
  );
}

const plans = [
  { name: "Free", price: "$0", detail: "Empieza con un plan diario y tus bibliotecas esenciales.", tone: tokens.color.textMuted },
  { name: "Basic", price: "$3.990", detail: "Bibliotecas ilimitadas y 150 créditos mensuales.", tone: tokens.color.interactivePrimary, recommended: true },
  { name: "Pro", price: "$6.990", detail: "1.000 créditos para un uso intensivo.", tone: tokens.color.program },
] as const;

function PlansView({ index }: { index: number }) {
  return (
    <>
      <StepHeader description="Compara lo que incluyen Free, Basic y Pro. Puedes cambiar de plan más adelante." eyebrow="Planes disponibles" icon={BookOpen} index={index} title="Elige un plan" />
      <View style={styles.planList}>
        {plans.map((plan) => (
          <View key={plan.name} style={[styles.planCard, plan.recommended && styles.planCardRecommended]}>
            <View style={styles.planHeading}><View style={styles.flex}><Text style={styles.planName}>{plan.name}</Text>{plan.recommended ? <Text style={styles.recommended}>RECOMENDADO</Text> : null}</View><Text style={[styles.planPrice, { color: plan.tone }]}>{plan.price}<Text style={styles.planPeriod}>/mes</Text></Text></View>
            <Text style={styles.planDetail}>{plan.detail}</Text>
            <Button label={plan.name === "Free" ? "Continuar con Free" : `Elegir ${plan.name}`} onPress={noop} variant={plan.name === "Basic" ? "primary" : "secondary"} />
          </View>
        ))}
      </View>
      <Text style={styles.quietCenter}>Precios mensuales en CLP. También habrá opciones anuales.</Text>
    </>
  );
}

function HomeView({ index }: { index: number }) {
  return (
    <>
      <Brand compact />
      <StepHeader description="Ahora puedes crear un plan diario a partir de tu objetivo y tus datos." eyebrow="Siguiente paso" icon={Home} index={index} title="Tu ficha está lista" />
      <Card accent={tokens.color.dailyPlan}>
        <Text style={styles.cardEyebrow}>SIGUIENTE PASO</Text>
        <Text style={styles.cardTitle}>Crea tu primer plan diario</Text>
        <Text style={textStyles.muted}>Partiremos de tu objetivo y punto de partida. Podrás revisar cada alimento y cantidad antes de guardarlo.</Text>
        <Button label="Crear mi primer plan" onPress={noop} />
      </Card>
      <View style={styles.homeActions}><Pill label="Ficha completa" color={tokens.color.success} /><Pill label="Plan Free" color={tokens.color.textMuted} /></View>
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
  summary: SummaryView,
  plans: PlansView,
  home: HomeView,
};

export function OnboardingJourneyView({ step }: { step: OnboardingJourneyStep }) {
  const index = onboardingJourneySteps.findIndex((item) => item.key === step);
  const ViewComponent = views[step];
  return <View style={styles.screen}><ViewComponent index={index} /></View>;
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, gap: tokens.spacing.lg, minHeight: 690, paddingBottom: tokens.spacing.xl, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  intro: { alignItems: "flex-start", gap: tokens.spacing.sm },
  stepMeta: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, width: "100%" },
  stepCount: { color: tokens.color.textSoft, fontSize: 10, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, letterSpacing: 1 },
  progressTrack: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, flex: 1, height: 3, overflow: "hidden" },
  progressFill: { backgroundColor: tokens.color.interactivePrimary, height: "100%" },
  iconWell: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, height: 54, justifyContent: "center", marginTop: tokens.spacing.sm, width: 54 },
  eyebrow: { color: tokens.color.interactivePrimary, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, letterSpacing: 1.2, textTransform: "uppercase" },
  title: { color: tokens.color.textMain, fontSize: 28, fontWeight: tokens.weight.extraBold, letterSpacing: -0.8, lineHeight: 32 },
  description: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  footer: { gap: tokens.spacing.sm, marginTop: "auto" },
  backAction: { alignItems: "center", alignSelf: "center", flexDirection: "row", gap: tokens.spacing.xs, minHeight: 40, paddingHorizontal: tokens.spacing.md },
  backLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  explanationCard: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.md, padding: tokens.spacing.md },
  explanationIcon: { alignItems: "center", backgroundColor: tokens.color.surfaceElevated, borderRadius: tokens.radius.md, height: 36, justifyContent: "center", width: 36 },
  explanationCopy: { flex: 1, gap: 2 },
  explanationTitle: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  explanationBody: { color: tokens.color.textMuted, fontSize: 12, lineHeight: 17 },
  loginHero: { gap: tokens.spacing.md, marginTop: 32 },
  loginKicker: { color: tokens.color.program, fontSize: 11, fontWeight: tokens.weight.extraBold, letterSpacing: 1.5 },
  loginTitle: { color: tokens.color.textMain, fontSize: 32, fontWeight: tokens.weight.extraBold, letterSpacing: -1, lineHeight: 37 },
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
  panelEyebrow: { color: tokens.color.dailyPlan, fontSize: 10, fontWeight: tokens.weight.bold, letterSpacing: 1 },
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
  optionCard: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.lg, borderWidth: 1, flexDirection: "row", justifyContent: "space-between", minHeight: 50, paddingHorizontal: tokens.spacing.lg },
  optionCardSelected: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  optionText: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  optionTextSelected: { color: tokens.color.surfaceApp },
  measurementFields: { flexDirection: "row", gap: tokens.spacing.md },
  flex: { flex: 1 },
  fieldLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  activityList: { gap: tokens.spacing.sm },
  activityOption: { alignItems: "center", borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.md, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.md, padding: tokens.spacing.md },
  activityOptionSelected: { backgroundColor: tokens.color.surfaceElevated, borderColor: tokens.color.interactivePrimary },
  activityLabel: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  activityDetail: { color: tokens.color.textMuted, fontSize: 11, marginTop: 2 },
  radio: { alignItems: "center", borderColor: tokens.color.borderStrong, borderRadius: 10, borderWidth: 1, height: 20, justifyContent: "center", width: 20 },
  radioSelected: { borderColor: tokens.color.interactivePrimary },
  radioDot: { backgroundColor: tokens.color.interactivePrimary, borderRadius: 5, height: 10, width: 10 },
  summaryHero: { alignItems: "center", gap: 2, paddingVertical: tokens.spacing.sm },
  summaryValue: { color: tokens.color.textMain, fontSize: 38, fontWeight: tokens.weight.extraBold, letterSpacing: -1.2 },
  summaryUnit: { color: tokens.color.textMuted, fontSize: 12 },
  summaryGrid: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  summaryCell: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, gap: 3, padding: tokens.spacing.sm, width: "48%" },
  summaryLabel: { color: tokens.color.textSoft, fontSize: 10, textTransform: "uppercase" },
  summaryText: { color: tokens.color.textMain, fontSize: 12, fontWeight: tokens.weight.bold },
  planList: { gap: tokens.spacing.sm },
  planCard: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, gap: tokens.spacing.sm, padding: tokens.spacing.md },
  planCardRecommended: { borderColor: tokens.color.interactivePrimary, borderWidth: 2 },
  planHeading: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "space-between" },
  planName: { color: tokens.color.textMain, fontSize: 18, fontWeight: tokens.weight.extraBold },
  recommended: { color: tokens.color.interactivePrimary, fontSize: 9, fontWeight: tokens.weight.bold, letterSpacing: 0.8, marginTop: 2 },
  planPrice: { fontSize: 17, fontWeight: tokens.weight.extraBold },
  planPeriod: { color: tokens.color.textSoft, fontSize: 10, fontWeight: tokens.weight.medium },
  planDetail: { color: tokens.color.textMuted, fontSize: 11, lineHeight: 16 },
  cardEyebrow: { color: tokens.color.dailyPlan, fontSize: 10, fontWeight: tokens.weight.bold, letterSpacing: 1 },
  homeActions: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
});
