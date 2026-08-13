export type AsyncJobStatus = "queued" | "running" | "retrying" | "succeeded";

export type AsyncJobSnapshot<TResult> = {
  job_id: string;
  status: AsyncJobStatus;
  retry_after_ms: number | null;
  result: TResult | null;
};

type PollAsyncJobOptions<TResult> = {
  path: string;
  request(path: string): Promise<AsyncJobSnapshot<TResult>>;
  signal?: AbortSignal;
  maxPolls?: number;
  defaultRetryAfterMs?: number;
  maxRetryAfterMs?: number;
  wait?: (delayMs: number, signal?: AbortSignal) => Promise<void>;
};

export class AsyncJobProtocolError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AsyncJobProtocolError";
  }
}

export class AsyncJobTimeoutError extends Error {
  constructor() {
    super("La operación sigue en curso. Puedes volver a intentarlo en unos instantes.");
    this.name = "AsyncJobTimeoutError";
  }
}

function abortError(): Error {
  const error = new Error("La espera fue cancelada.");
  error.name = "AbortError";
  return error;
}

export function waitForAsyncJob(delayMs: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return Promise.reject(abortError());
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, Math.max(0, delayMs));
    const onAbort = () => {
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
      reject(abortError());
    };
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

export async function pollAsyncJob<TResult>({
  path,
  request,
  signal,
  maxPolls = 80,
  defaultRetryAfterMs = 750,
  maxRetryAfterMs = 5_000,
  wait = waitForAsyncJob,
}: PollAsyncJobOptions<TResult>): Promise<TResult> {
  const boundedPolls = Math.max(1, maxPolls);
  for (let poll = 0; poll < boundedPolls; poll += 1) {
    if (signal?.aborted) throw abortError();
    const snapshot = await request(path);
    if (snapshot.status === "succeeded") {
      if (snapshot.result === null) {
        throw new AsyncJobProtocolError("La operación terminó sin entregar un resultado válido.");
      }
      return snapshot.result;
    }
    if (poll === boundedPolls - 1) break;
    const requestedDelay = snapshot.retry_after_ms ?? defaultRetryAfterMs;
    const delay = Math.min(Math.max(0, requestedDelay), maxRetryAfterMs);
    await wait(delay, signal);
  }
  throw new AsyncJobTimeoutError();
}
