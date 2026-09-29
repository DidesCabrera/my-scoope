import { useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";

import { userFacingError } from "@/api/errors";
import type { ProposalDetail } from "@/api/types";
import { useSession } from "@/auth/session-context";

export function useProposalDetail(id: string | undefined) {
  const { apiRequest, status } = useSession();
  const [proposal, setProposal] = useState<ProposalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setProposal(await apiRequest<ProposalDetail>(`/api/v1/proposals/${id}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, id]);

  useFocusEffect(useCallback(() => {
    if (status === "authenticated") void load();
  }, [load, status]));

  return { error, load, loading, proposal, status };
}
