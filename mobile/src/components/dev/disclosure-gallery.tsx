import { StyleSheet, Text, View } from "react-native";

import { AppHeader, Brand, Button, Card, InlineNotice, SectionTitle, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";

const noop = () => undefined;

export function DisclosureGallery() {
  return (
    <>
      <SectionTitle detail="Vista aislada · sin aceptación, navegación ni persistencia" title="Responsabilidades de la cuenta" />
      <InlineNotice>Esta representación corresponde a la divulgación obligatoria que puede aparecer después de iniciar sesión. Sus controles son solo visuales.</InlineNotice>
      <View style={styles.preview}>
        <View style={styles.previewMeta}>
          <Text style={styles.previewName}>Información importante</Text>
          <Text style={styles.previewWidth}>414 pt</Text>
        </View>
        <View style={styles.devicePreview}>
          <Brand />
          <AppHeader eyebrow="Antes de comenzar" title="Tu decisión sigue siendo la última" />
          <Text style={textStyles.muted}>My Scoope está hecho para personas que gestionan activamente su alimentación y quieren ejecutar un programa con disciplina.</Text>
          <Card accent={tokens.color.warning}>
            <SectionTitle title="No es atención médica" />
            <Text style={textStyles.body}>La app no diagnostica, trata ni reemplaza a un médico o nutricionista. Si tienes una condición médica, síntomas, embarazo o restricciones clínicas, consulta a un profesional.</Text>
          </Card>
          <Card accent={tokens.color.interactivePrimary}>
            <SectionTitle title="Revisa antes de aplicar" />
            <Text style={textStyles.body}>Los cálculos, lecturas de etiquetas y propuestas asistidas por IA pueden contener errores. Confirma cantidades, ingredientes y cambios antes de usarlos.</Text>
          </Card>
          <Card muted>
            <SectionTitle title="Privacidad y control" />
            <Text style={textStyles.muted}>Si digitalizas una etiqueta, una copia reducida y sin metadatos se envía temporalmente a OpenAI para extraer sus valores. My Scoope no guarda esa foto salvo que tú actives expresamente “Guardar copia procesada”; podrás verla y eliminarla después. Puedes revisar nuestra política y eliminar tu cuenta desde la app.</Text>
            <Button label="Leer política de privacidad" onPress={noop} variant="secondary" />
            <Button label="Leer términos de uso" onPress={noop} variant="secondary" />
            <Button label="Leer política de reembolsos" onPress={noop} variant="secondary" />
          </Card>
          <Button label="Entiendo y quiero continuar" onPress={noop} />
          <Text style={textStyles.caption}>Confirmación label-ai.v1</Text>
        </View>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  preview: { alignSelf: "center", gap: tokens.spacing.sm, maxWidth: "100%", width: 414 },
  previewMeta: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", paddingHorizontal: tokens.spacing.sm },
  previewName: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  previewWidth: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"] },
  devicePreview: { alignSelf: "center", backgroundColor: tokens.color.surfacePage, borderColor: tokens.color.borderStrong, borderRadius: 30, borderWidth: 1, gap: tokens.spacing.lg, maxWidth: "100%", overflow: "hidden", padding: tokens.spacing.screen, width: "100%" },
});
