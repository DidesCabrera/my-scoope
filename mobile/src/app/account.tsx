import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import * as Linking from "expo-linking";
import { Flag, LifeBuoy, Pencil, Trash2 } from "lucide-react-native";
import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";
import { useCallback, useState } from "react";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { AccountDeletionData, EntitlementsData, SessionData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AssistantCreditBalance } from "@/components/assistant/assistant-credit-balance";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProposalReviewSection } from "@/components/proposals/proposal-detail";
import { AppHeader, Button, Card, Field, InlineNotice, Screen, SectionIcon, textStyles } from "@/components/ui";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { appConfig } from "@/config/app-config";
import { tokens } from "@/design/tokens";
import { subscriptionPlanAccent } from "@/presentation/subscription";

const supportEmail = "felipe@myscoope.com";

function joinedDateLabel(value?: string): string {
  if (!value) return "No disponible";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "No disponible";
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" }).format(date);
}

export default function AccountScreen() {
  const router = useRouter();
  const { status, session, apiRequest, refreshSession, signOut } = useSession();
  const [confirmation, setConfirmation] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entitlements, setEntitlements] = useState<EntitlementsData | null>(null);
  const [subscriptionError, setSubscriptionError] = useState<string | null>(null);
  const [accountActions, setAccountActions] = useState<"menu" | "rename" | "delete" | null>(null);
  const [accountActionsVisible, setAccountActionsVisible] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const setHeaderPresentation = useHeaderPresentation();

  const openAccountActions = useCallback(() => {
    setUsername(session?.username ?? "");
    setAccountActions("menu");
    setAccountActionsVisible(true);
  }, [session?.username]);
  const closeAccountActions = useCallback(() => {
    setAccountActionsVisible(false);
  }, []);
  const finishClosingAccountActions = useCallback(() => {
    setAccountActions(null);
    setConfirmation("");
    setPassword("");
    setUsername("");
    setError(null);
  }, []);

  const openExternalAction = useCallback((url: string) => {
    setAccountActionsVisible(false);
    void Linking.openURL(url);
  }, []);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: { label: "Acciones de mi cuenta", onPress: openAccountActions },
      identityVisible: compactHeaderVisible,
      mode: "default",
      title: "Mi cuenta",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, openAccountActions, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated") return;
    setSubscriptionError(null);
    void apiRequest<EntitlementsData>("/api/v1/entitlements")
      .then(setEntitlements)
      .catch((nextError) => setSubscriptionError(userFacingError(nextError)));
  }, [apiRequest, status]));

  if (status === "anonymous") return <Redirect href="/login" />;

  async function deleteAccount() {
    setBusy(true);
    setError(null);
    try {
      const result = await apiRequest<AccountDeletionData>("/api/v1/account/delete", {
        method: "POST",
        body: JSON.stringify({ confirmation, password }),
      });
      await signOut();
      Alert.alert("Cuenta eliminada", `Tu acceso fue revocado. Comprobante: ${result.receipt_id}`);
      router.replace("/login");
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function renameUsername() {
    const cleanUsername = username.trim();
    if (!cleanUsername) return;
    setBusy(true);
    setError(null);
    try {
      await apiRequest<SessionData>("/api/v1/account/username", {
        method: "PATCH",
        body: JSON.stringify({ username: cleanUsername }),
      });
      await refreshSession();
      setAccountActionsVisible(false);
      Alert.alert("Nombre de usuario actualizado", `Ahora tu nombre de usuario es “${cleanUsername}”.`);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible}>
      <AppHeader eyebrow="Mi cuenta" eyebrowIcon={<SectionIcon color={tokens.color.textSoft} section="profile" />} title={session?.display_name || session?.username || "My Scoope"} />
      <Card accent={subscriptionPlanAccent(entitlements?.plan_name)}>
        <View style={styles.subscriptionHeading}>
          <View style={styles.headerCopy}>
            <Text style={styles.eyebrow}>SUSCRIPCIÓN ACTUAL</Text>
            <Text style={styles.planName}>{entitlements?.plan_name ?? "Consultando…"}</Text>
          </View>
        </View>
        {entitlements ? <AssistantCreditBalance availability={entitlements} contained /> : null}
        {subscriptionError ? <InlineNotice tone="error">{subscriptionError}</InlineNotice> : null}
        <Button label="Mejorar mi suscripción" onPress={() => router.push("/subscription" as Href)} variant="multicolor" />
      </Card>
      <ProposalReviewSection eyebrow="INFORMACIÓN DE LA CUENTA">
        <AccountInformationRows items={[
          { label: "Nombre de usuario", value: session?.username ?? "—" },
          { label: "Correo electrónico", value: session?.email || "No disponible" },
          { label: "Fecha de ingreso", value: joinedDateLabel(session?.date_joined) },
        ]} />
      </ProposalReviewSection>
      <InlineNotice tone="warning">My Scoope no reemplaza atención médica. Revisa cualquier cálculo, lectura OCR o propuesta asistida por IA antes de aplicarla.</InlineNotice>
      {__DEV__ ? (
        <Button label="Abrir galería del sistema UI" onPress={() => router.push("/dev/ui-gallery" as Href)} variant="secondary" />
      ) : null}
      <Button label="Cerrar sesión" onPress={() => void signOut().then(() => router.replace("/login"))} variant="secondary" />
      <ActionSheetModal onDismiss={finishClosingAccountActions} onRequestClose={closeAccountActions} visible={accountActionsVisible}>
        <SafeAreaView edges={["left", "right"]} style={styles.sheetSafeArea}>
          <ActionSheetHeader onClose={closeAccountActions} section="profile" title={accountActions === "delete" ? "Eliminar mi cuenta" : accountActions === "rename" ? "Editar nombre de usuario" : "Mi cuenta"} />
          {accountActions === "menu" ? (
            <View style={styles.sheetContent}>
              <ActionSheetActions>
                <ActionSheetAction icon={Pencil} label="Editar nombre de usuario" onPress={() => { setUsername(session?.username ?? ""); setError(null); setAccountActions("rename"); }} />
                <ActionSheetAction icon={LifeBuoy} label="Centro de soporte" onPress={() => openExternalAction(`${appConfig.apiBaseUrl}/support/`)} />
                <ActionSheetAction icon={Flag} label="Reportar contenido o un problema" onPress={() => openExternalAction(`mailto:${supportEmail}?subject=Reporte%20desde%20My%20Scoope`)} />
                <ActionSheetAction destructive icon={Trash2} label="Eliminar cuenta" onPress={() => setAccountActions("delete")} />
              </ActionSheetActions>
            </View>
          ) : (
          <ScrollView contentContainerStyle={styles.sheetContent} keyboardShouldPersistTaps="handled" nestedScrollEnabled showsVerticalScrollIndicator={false} style={styles.sheetScroll}>
            {accountActions === "rename" ? (
              <View style={styles.deletionForm}>
                <Field autoCapitalize="none" autoCorrect={false} label="Nombre de usuario" onChangeText={(value) => setUsername(value.slice(0, 150))} value={username} />
                {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
                <Button disabled={!username.trim() || username.trim() === session?.username} label="Guardar nombre" loading={busy} onPress={() => void renameUsername()} />
                <Button disabled={busy} label="Volver" onPress={() => { setError(null); setAccountActions("menu"); }} variant="secondary" />
              </View>
            ) : accountActions === "delete" ? (
              <View style={styles.deletionForm}>
                <Text style={textStyles.muted}>Esta acción revoca el acceso inmediatamente y elimina o anonimiza tus datos conforme a nuestra política. No se puede deshacer.</Text>
                <Field autoCapitalize="characters" label="Escribe ELIMINAR para confirmar" onChangeText={setConfirmation} value={confirmation} />
                <Field label="Contraseña (si tu cuenta usa una)" onChangeText={setPassword} secureTextEntry value={password} />
                {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
                <Button disabled={confirmation !== "ELIMINAR"} label="Eliminar cuenta definitivamente" loading={busy} onPress={deleteAccount} variant="danger" />
                <Button label="Volver" onPress={() => setAccountActions("menu")} variant="secondary" />
              </View>
            ) : null}
          </ScrollView>
          )}
        </SafeAreaView>
      </ActionSheetModal>
    </Screen>
  );
}

function AccountInformationRows({ items }: { items: { label: string; value: string }[] }) {
  return (
    <View style={styles.informationRows}>
      {items.map((item, index) => (
        <View key={item.label} style={[styles.informationRow, index === items.length - 1 && styles.informationRowLast]}>
          <Text style={styles.informationLabel}>{item.label}</Text>
          <Text adjustsFontSizeToFit minimumFontScale={0.72} numberOfLines={1} selectable style={styles.informationValue}>{item.value}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  deletionForm: { gap: tokens.spacing.md },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1 },
  headerCopy: { flex: 1, gap: 3, minWidth: 0 },
  informationLabel: { color: tokens.color.textMuted, flex: 1, fontSize: 14, lineHeight: 20 },
  informationRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 46, paddingVertical: tokens.spacing.xs },
  informationRowLast: { borderBottomWidth: 0 },
  informationRows: { marginTop: -tokens.spacing.xs },
  informationValue: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontWeight: tokens.weight.bold, lineHeight: 20, textAlign: "right" },
  pressed: { opacity: 0.65 },
  sheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  sheetScroll: { flexGrow: 0, flexShrink: 1 },
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  planName: { color: tokens.color.textMain, fontSize: 26, fontWeight: tokens.weight.extraBold },
  subscriptionHeading: { alignItems: "center", flexDirection: "row" },
});
