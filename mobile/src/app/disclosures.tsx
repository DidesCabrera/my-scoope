import { type Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import * as Linking from "expo-linking";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ProfileData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ResponsibleUseActionButton, ResponsibleUseContent } from "@/components/disclosures/responsible-use-content";
import { Button, InlineNotice, Screen, textStyles } from "@/components/ui";
import { appConfig } from "@/config/app-config";
import { tokens } from "@/design/tokens";
import { internalHref } from "@/navigation/internal-href";

export default function DisclosuresScreen() {
  const { returnTo } = useLocalSearchParams<{ returnTo?: string }>();
  const returnHref = internalHref(returnTo);
  const router = useRouter();
  const { status, profile, apiRequest, refreshProfile } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (status === "anonymous") return <Redirect href={{ pathname: "/login", params: returnHref ? { returnTo: String(returnHref) } : {} }} />;
  if (status === "authenticated" && profile && !profile.review_disclosure_required) {
    if (!profile.onboarding_completed) return <Redirect href={{ pathname: "/onboarding", params: returnHref ? { returnTo: String(returnHref) } : {} }} />;
    return <Redirect href={returnHref ?? ("/today" as Href)} />;
  }

  async function accept() {
    setBusy(true);
    setError(null);
    try {
      await apiRequest<ProfileData>("/api/v1/account/disclosures", {
        method: "POST",
        body: JSON.stringify({ accepted: true }),
      });
      const nextProfile = await refreshProfile();
      if (!nextProfile.onboarding_completed) {
        router.replace({ pathname: "/onboarding", params: returnHref ? { returnTo: String(returnHref) } : {} });
      } else {
        router.replace(returnHref ?? ("/today" as Href));
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <ResponsibleUseContent policyActions={<View style={styles.policyActions}>
        <Button label="Leer política de privacidad" onPress={() => void Linking.openURL(`${appConfig.apiBaseUrl}/privacy/`)} variant="secondary" />
        <Button label="Leer términos de uso" onPress={() => void Linking.openURL(`${appConfig.apiBaseUrl}/terms/`)} variant="secondary" />
        <Button label="Leer política de reembolsos" onPress={() => void Linking.openURL(`${appConfig.apiBaseUrl}/refund-policy/`)} variant="secondary" />
      </View>} />
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      <ResponsibleUseActionButton loading={busy} onPress={accept} />
      <Text style={textStyles.caption}>Confirmación {profile?.review_disclosure_version ?? "cml08.v1"}</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  policyActions: { gap: tokens.spacing.sm },
});
