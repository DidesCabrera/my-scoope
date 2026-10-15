/** One account owns foreground refreshes. Focus/reconnect requests share a task;
 * a resume during an older task requests one follow-up. Only failures retry,
 * while active, and stop immediately after a successful refresh. */
export class ForegroundRefresh {
  private active: boolean;
  private alive = true;
  private task: Promise<void> | null = null;
  private followup = false;
  private cancelRetry: (() => void) | null = null;
  private failures = 0;
  private lifetime = new AbortController();

  constructor(private readonly deps: {
    refresh(signal: AbortSignal): Promise<void>;
    retry(error: unknown): boolean;
    schedule?(run: () => void, delay: number): () => void;
  }, initialState: string | null) { this.active = initialState === "active"; }

  transition(next: string): void {
    const wasActive = this.active;
    this.active = next === "active";
    if (!this.active) { this.cancelRetry?.(); this.cancelRetry = null; return; }
    if (!wasActive) {
      if (this.task) this.followup = true;
      void this.refresh().catch(() => undefined);
    }
  }

  dispose(): void {
    this.alive = false;
    this.lifetime.abort();
    this.cancelRetry?.();
    this.cancelRetry = null;
  }

  refresh(): Promise<void> {
    if (!this.alive || !this.active) return Promise.resolve();
    if (this.task) return this.task;
    this.cancelRetry?.();
    this.cancelRetry = null;
    const task = this.run();
    this.task = task;
    const clear = () => { if (this.task === task) this.task = null; };
    void task.then(clear, clear);
    return task;
  }

  private async run(): Promise<void> {
    let failed = false;
    let failure: unknown;
    do {
      this.followup = false;
      try { await this.deps.refresh(this.lifetime.signal); failed = false; this.failures = 0; }
      catch (error) { failed = true; failure = error; }
    } while (this.followup && this.alive && this.active);
    if (!failed) return;
    if (this.alive && this.active && this.deps.retry(failure)) {
      const delay = [3_000, 6_000, 15_000][Math.min(this.failures++, 2)];
      const schedule = this.deps.schedule ?? ((run: () => void, milliseconds: number) => {
        const timer = setTimeout(run, milliseconds);
        return () => clearTimeout(timer);
      });
      this.cancelRetry = schedule(() => {
        this.cancelRetry = null;
        void this.refresh().catch(() => undefined);
      }, delay);
    }
    throw failure;
  }
}
