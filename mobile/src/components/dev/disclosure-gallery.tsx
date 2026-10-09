import { StyleSheet, Text, View } from "react-native";

import { ResponsibleUseActionButton, ResponsibleUseContent } from "@/components/disclosures/responsible-use-content";
import { Button, InlineNotice, SectionTitle, textStyles } from "@/components/ui";
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
          <ResponsibleUseContent policyActions={<View style={styles.policyActions}>
            <Button label="Leer política de privacidad" onPress={noop} variant="secondary" />
            <Button label="Leer términos de uso" onPress={noop} variant="secondary" />
            <Button label="Leer política de reembolsos" onPress={noop} variant="secondary" />
          </View>} />
          <ResponsibleUseActionButton label="Entiendo y quiero continuar" onPress={noop} />
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
  devicePreview: { alignSelf: "center", backgroundColor: tokens.color.surfaceApp, borderColor: tokens.color.borderStrong, borderRadius: 30, borderWidth: 1, gap: tokens.spacing.lg, maxWidth: "100%", overflow: "hidden", padding: tokens.spacing.screen, width: "100%" },
  policyActions: { gap: tokens.spacing.sm },
});
