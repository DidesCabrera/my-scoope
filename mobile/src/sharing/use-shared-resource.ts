import { useEffect, useState } from "react";

import { userFacingError } from "@/api/errors";
import type { ApiEnvelope, ShareResource } from "@/api/types";
import { appConfig } from "@/config/app-config";

export function useSharedResource(id?: string) {
  const [resource, setResource] = useState<ShareResource | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let active = true;
    void fetch(`${appConfig.apiBaseUrl}/api/v1/shares/${id}`)
      .then(async (response) => {
        const payload = await response.json() as ApiEnvelope<ShareResource>;
        if (!response.ok || !payload.ok) throw new Error(payload.ok ? "share_unavailable" : payload.error.message);
        if (active) setResource(payload.data);
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  return { error, loading, resource };
}
