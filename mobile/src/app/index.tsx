import { Redirect } from "expo-router";

import { useSession } from "@/auth/session-context";
import { LoadingState } from "@/components/ui/primitives";

export default function Index() {
  const { status, profile } = useSession();
  if (status === "booting") return <LoadingState />;
  if (status === "anonymous") return <Redirect href="/login" />;
  if (profile?.review_disclosure_required) return <Redirect href="./disclosures" />;
  if (!profile?.onboarding_completed) return <Redirect href="/onboarding" />;
  return <Redirect href="/today" />;
}
