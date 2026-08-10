import { Redirect } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import {
  KpiAllocationBar,
  MacroSummary,
  NutrientProgress,
  NutritionMetric,
  PanelAllocationBar,
} from "@/components/nutrition";
import {
  AppHeader,
  Brand,
  Button,
  Card,
  ChoiceRow,
  CollectionEmptyState,
  ContentPanel,
  DetailSection,
  EntityCard,
  type EntityKind,
  Field,
  InlineNotice,
  MessageCard,
  PanelTabs,
  Pill,
  ProgressBar,
  Screen,
  SectionTitle,
  textStyles,
} from "@/components/ui";
import { tokens } from "@/design/tokens";

const entities: { key: EntityKind; label: string }[] = [
  { key: "food", label: "Food" },
  { key: "meal", label: "Meal" },
  { key: "dailyPlan", label: "DailyPlan" },
  { key: "dpm", label: "DPM" },
  { key: "program", label: "Program" },
  { key: "proposal", label: "Proposal" },
  { key: "inbox", label: "Inbox" },
  { key: "comparator", label: "Comparator" },
  { key: "home", label: "Home" },
  { key: "profile", label: "Profile" },
];

type GalleryTab = "components" | "states" | "tokens";
type Choice = "daily" | "weekly";

export default function UiGalleryScreen() {
  const [tab, setTab] = useState<GalleryTab>("components");
  const [choice, setChoice] = useState<Choice>("daily");
  const [field, setField] = useState("");

  if (!__DEV__) return <Redirect href="/" />;

  return (
    <Screen>
      <Brand />
      <AppHeader eyebrow="Solo desarrollo" title="Galería del sistema UI" />
      <InlineNotice>Referencia interna construida con los componentes reales de la app.</InlineNotice>
      <PanelTabs
        activeTab={tab}
        onChange={setTab}
        tabs={[
          { key: "components", label: "Componentes" },
          { key: "states", label: "Estados" },
          { key: "tokens", label: "Tokens" },
        ]}
      />

      {tab === "components" ? (
        <>
          <SectionTitle detail="Jerarquía compartida" title="Producto" />
          <ContentPanel description="Panel principal que agrupa información relacionada." title="ContentPanel">
            <DetailSection description="Sección anidada con encabezado y acción opcional." title="DetailSection">
              <Text style={textStyles.body}>Contenido compuesto sin replicar estilos de superficie.</Text>
            </DetailSection>
          </ContentPanel>
          <EntityCard
            accessory={<Pill color={tokens.color.dailyPlan} label="Activo" />}
            entity="dailyPlan"
            eyebrow="Plan de hoy"
            subtitle="4 comidas · 2.140 kcal"
            title="Día de entrenamiento">
            <Text style={textStyles.muted}>EntityCard y EntityHeading comparten el color semántico de la entidad.</Text>
          </EntityCard>
          <CollectionEmptyState
            actionLabel="Crear elemento"
            description="Este estado mantiene la acción principal junto al contexto de la colección."
            onAction={() => undefined}
            title="Todavía no hay elementos"
          />

          <SectionTitle detail="Resumen y progreso" title="Nutrición" />
          <Card>
            <MacroSummary totals={{ total_kcal: 2140, protein_g: 155, carbs_g: 238, fat_g: 62 }} />
            <NutrientProgress color={tokens.color.protein} label="Proteína" target={180} value={155} />
            <NutrientProgress color={tokens.color.carbs} label="Carbohidratos" target={260} value={238} />
            <NutritionMetric color={tokens.color.ppk} label="Proteína por kilo" unit="g/kg" value="1,8" />
          </Card>

          <SectionTitle detail="Identidad de marca" title="Alloc en KPI" />
          <Card>
            <View style={styles.allocationRow}>
              <Text style={styles.allocationLabel}>Proteína</Text>
              <KpiAllocationBar style={styles.allocationBarInRow} tone="protein" value={72} />
            </View>
            <View style={styles.allocationRow}>
              <Text style={styles.allocationLabel}>Carbohidratos</Text>
              <KpiAllocationBar style={styles.allocationBarInRow} tone="carbs" value={48} />
            </View>
            <View style={styles.allocationRow}>
              <Text style={styles.allocationLabel}>Grasas</Text>
              <KpiAllocationBar style={styles.allocationBarInRow} tone="fat" value={26} />
            </View>
          </Card>

          <SectionTitle detail="Regular y compacta" title="Alloc en paneles" />
          <ContentPanel description="El mismo porcentaje base cambia de composición según su contexto." title="Distribución objetivo">
            <View style={styles.allocationRow}>
              <Text style={styles.allocationLabel}>Proteína</Text>
              <PanelAllocationBar style={styles.allocationBarInRow} tone="protein" value={84} />
            </View>
            <View style={styles.allocationRow}>
              <Text style={styles.allocationLabel}>Carbohidratos</Text>
              <PanelAllocationBar style={styles.allocationBarInRow} tone="carbs" value={51} />
            </View>
            <View style={styles.allocationRow}>
              <Text style={styles.allocationLabel}>Grasas</Text>
              <PanelAllocationBar style={styles.allocationBarInRow} tone="fat" value={18} />
            </View>
            <DetailSection description="Para filas densas, pickers y cards secundarias." title="Tamaño compacto">
              <PanelAllocationBar size="compact" tone="protein" value={100} />
              <PanelAllocationBar size="compact" tone="carbs" value={4} />
              <PanelAllocationBar size="compact" tone="fat" value={0} />
            </DetailSection>
          </ContentPanel>
        </>
      ) : null}

      {tab === "states" ? (
        <>
          <SectionTitle detail="Interactivos" title="Controles" />
          <Button label="Acción principal" onPress={() => undefined} />
          <Button label="Acción secundaria" onPress={() => undefined} variant="secondary" />
          <Button label="Acción destructiva" onPress={() => undefined} variant="danger" />
          <Button disabled label="Acción deshabilitada" onPress={() => undefined} />
          <Button label="Procesando" loading onPress={() => undefined} />
          <Field label="Campo de ejemplo" onChangeText={setField} placeholder="Escribe un valor" value={field} />
          <ChoiceRow<Choice>
            label="Frecuencia"
            onChange={setChoice}
            options={[{ value: "daily", label: "Diaria" }, { value: "weekly", label: "Semanal" }]}
            value={choice}
          />
          <ProgressBar value={64} />
          <InlineNotice>Información contextual.</InlineNotice>
          <InlineNotice tone="warning">Requiere atención antes de continuar.</InlineNotice>
          <InlineNotice tone="error">No fue posible completar la acción.</InlineNotice>
          <MessageCard title="Cambio guardado" tone="success">La configuración ya está disponible en tus dispositivos.</MessageCard>
          <MessageCard title="Revisión pendiente" tone="warning">Confirma los datos nutricionales antes de aplicarlos.</MessageCard>
          <MessageCard title="Error de sincronización" tone="danger">Conservamos tus cambios locales para reintentarlo.</MessageCard>
        </>
      ) : null}

      {tab === "tokens" ? (
        <>
          <SectionTitle detail={tokens.contract} title="Entidades" />
          {entities.map((entity) => (
            <EntityCard entity={entity.key} key={entity.key} subtitle={`tokens.color.${entity.key}`} title={entity.label} />
          ))}
          <SectionTitle detail="Escala semántica" title="Tipografía" />
          {Object.entries(tokens.type).map(([name, size]) => (
            <View key={name} style={styles.typeRow}>
              <Text style={[styles.typeSample, { fontSize: size }]}>{name}</Text>
              <Text style={textStyles.caption}>{size} pt</Text>
            </View>
          ))}
          <SectionTitle detail="xs → xxl" title="Espaciado" />
          {Object.entries(tokens.spacing).map(([name, size]) => (
            <View key={name} style={styles.scaleRow}>
              <Text style={styles.scaleLabel}>{name}</Text>
              <View style={[styles.scaleBar, { width: size * 3 }]} />
              <Text style={textStyles.caption}>{size}</Text>
            </View>
          ))}
          <SectionTitle detail="sm → pill" title="Radios" />
          <View style={styles.radiusGrid}>
            {Object.entries(tokens.radius).map(([name, radius]) => (
              <View key={name} style={styles.radiusItem}>
                <View style={[styles.radiusSample, { borderRadius: radius }]} />
                <Text style={textStyles.caption}>{name} · {radius}</Text>
              </View>
            ))}
          </View>
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  typeRow: { alignItems: "baseline", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingVertical: tokens.spacing.sm },
  typeSample: { color: tokens.color.textMain, fontWeight: "800" },
  scaleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, minHeight: 34 },
  scaleLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, width: 48 },
  scaleBar: { backgroundColor: tokens.color.interactivePrimary, borderRadius: tokens.radius.pill, height: 8 },
  radiusGrid: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.md },
  radiusItem: { alignItems: "center", gap: tokens.spacing.sm, width: "29%" },
  radiusSample: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.interactivePrimary, borderWidth: 1, height: 58, width: 58 },
  allocationRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  allocationLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700", width: 96 },
  allocationBarInRow: { flex: 1, minWidth: 0, width: "auto" },
});
