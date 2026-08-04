export function createIdempotencyKey(cryptoApi = globalThis.crypto) {
  if (cryptoApi && typeof cryptoApi.randomUUID === "function") return cryptoApi.randomUUID();
  return String(Date.now()) + "-" + Math.random().toString(16).slice(2);
}

export async function pollJob(statusUrl, options = {}) {
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  const delayImpl = options.delayImpl || ((milliseconds) => new Promise((resolve) => {
    globalThis.setTimeout(resolve, milliseconds);
  }));
  const maxNetworkFailures = options.maxNetworkFailures ?? 5;
  let networkFailures = 0;

  while (true) {
    let response;
    try {
      response = await fetchImpl(statusUrl, {
        method: "GET",
        headers: { "Accept": "application/json" },
        credentials: "same-origin"
      });
    } catch (error) {
      if (networkFailures >= maxNetworkFailures) throw error;
      await delayImpl(Math.min(1000 * Math.pow(2, networkFailures), 10000));
      networkFailures += 1;
      continue;
    }

    const payload = await response.json();
    if (response.status === 202) {
      networkFailures = 0;
      await delayImpl(Math.max(500, payload.retry_after_ms || 750));
      continue;
    }
    if (!response.ok) {
      const error = new Error(payload.error || "async_job_failed");
      error.code = payload.error || "async_job_failed";
      error.status = response.status;
      throw error;
    }
    return payload;
  }
}
