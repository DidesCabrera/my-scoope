/** Only the explicitly started browser attempt can update the session UI. */
export class AuthorizationFlow {
  private generation = 0;
  private state: string | null = null;
  get version(): number { return this.generation; }
  start(state: string): number { this.state = state; return ++this.generation; }
  invalidate(): void { this.state = null; this.generation += 1; }
  accepts(state: string | null | undefined): boolean { return Boolean(this.state && state === this.state); }
  isCurrent(version: number): boolean { return version === this.generation && this.state !== null; }

  async complete<T>(state: string | null | undefined, work: () => Promise<T>): Promise<T | null> {
    if (!this.accepts(state)) return null;
    const generation = this.generation;
    try {
      const result = await work();
      return this.isCurrent(generation) ? result : null;
    } catch (error) {
      if (!this.isCurrent(generation)) return null;
      throw error;
    }
  }
}
