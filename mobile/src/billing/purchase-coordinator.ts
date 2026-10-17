import type { EntitlementsData, SubscriptionData } from "../api/billing-types";

export type StorePurchase = {
  id: string; productId: string; purchaseToken?: string | null;
  purchaseState: "pending" | "purchased" | "unknown"; appAccountToken?: string | null;
  transactionDate?: number;
  reasonIOS?: string | null;
  transactionReasonIOS?: string | null;
};
export type BillingState = {
  overview: SubscriptionData | null; entitlements: EntitlementsData | null;
  phase: "idle" | "store" | "verifying" | "activating" | "pending" | "active" | "scheduled" | "credited" | "refunded";
  productId: string; planName: string | null; busy: boolean;
  message: string | null; error: string | null; refreshError: string | null; finishPending: boolean;
};
type Dependencies = {
  provider: "apple_app_store" | "google_play";
  apiRequest<T>(path: string, init?: RequestInit): Promise<T>;
  finish(purchase: StorePurchase, consumable: boolean): Promise<void>;
  errorMessage(error: unknown): string;
  wait?(milliseconds: number, signal: AbortSignal): Promise<void>;
  requestTimeoutMs?: number;
  now?(): number;
};
type TransactionRecord = { task: Promise<boolean>; accepted: boolean; finished: boolean; completed: boolean; phase?: BillingState["phase"] };

const activationDelays = [1_500, 3_000, 6_000, 12_000];
const initialState: BillingState = {
  overview: null, entitlements: null, phase: "idle", productId: "", planName: null,
  busy: false, message: null, error: null, refreshError: null, finishPending: false,
};
function wait(milliseconds: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const complete = () => { clearTimeout(timer); signal.removeEventListener("abort", complete); resolve(); };
    const timer = setTimeout(complete, milliseconds);
    signal.addEventListener("abort", complete, { once: true });
    if (signal.aborted) complete();
  });
}

/** One account owns this coordinator. Store evidence is serialized and never
 * finished before server acceptance. No receipt/token is written to storage. */
export class PurchaseCoordinator {
  state: BillingState = { ...initialState };
  private listeners = new Set<(state: BillingState) => void>();
  private lifetime = new AbortController();
  private queue: Promise<unknown> = Promise.resolve();
  private transactions = new Map<string, TransactionRecord>();
  private read: Promise<void> | null = null;
  private activation: Promise<void> | null = null;
  private snapshotVersion = 0;
  private queued = 0;
  private reconciliation: Promise<void> | null = null;
  private requestedGoal: string | null = null;
  private awaitingCredits = false;
  private noticeEnabled = false;
  private action: { productId: string; startedAt: number; hasReceipt: boolean; sheetCompleted: boolean; alreadyScheduled: boolean } | null = null;

  constructor(private readonly deps: Dependencies) {}
  subscribe(listener: (state: BillingState) => void): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => { this.listeners.delete(listener); };
  }
  dispose(): void { this.lifetime.abort(); this.listeners.clear(); }
  private get alive(): boolean { return !this.lifetime.signal.aborted; }
  private update(patch: Partial<BillingState>): void {
    if (!this.alive) return;
    if (patch.message && patch.phase !== "pending") {
      const success = ["active", "credited", "refunded"].includes(patch.phase ?? "");
      const scheduled = patch.phase === "scheduled";
      if (!this.noticeEnabled || (success && !this.action?.hasReceipt)
        || (scheduled && !this.action?.hasReceipt && (!this.action?.sheetCompleted || this.action.alreadyScheduled))) {
        patch = { ...patch, message: null };
      }
    }
    this.state = { ...this.state, ...patch };
    for (const listener of this.listeners) listener(this.state);
  }
  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const controller = new AbortController();
    const abort = () => controller.abort();
    const signals = [this.lifetime.signal, init.signal].filter((signal): signal is AbortSignal => Boolean(signal));
    for (const signal of signals) {
      signal.addEventListener("abort", abort, { once: true });
      if (signal.aborted) abort();
    }
    const deadline = setTimeout(abort, this.deps.requestTimeoutMs ?? 20_000);
    try { return await this.deps.apiRequest<T>(path, { ...init, signal: controller.signal }); }
    finally {
      clearTimeout(deadline);
      for (const signal of signals) signal.removeEventListener("abort", abort);
    }
  }
  begin(productId: string): boolean {
    if (!this.alive || this.queued > 0 || this.state.busy || ["pending", "activating"].includes(this.state.phase)) return false;
    if (this.state.entitlements?.credit_status && this.state.entitlements.credit_status !== "ready") return false;
    const plan = this.state.overview?.products.find((product) => product.provider === this.deps.provider && product.product_id === productId);
    const pack = this.state.overview?.credit_packs.find((product) => product.provider === this.deps.provider && product.product_id === productId);
    if ((!plan && !pack) || (pack && !this.state.overview?.can_buy_credit_packs)) return false;
    this.requestedGoal = productId;
    this.action = { productId, startedAt: (this.deps.now ?? Date.now)(), hasReceipt: false, sheetCompleted: false,
      alreadyScheduled: Boolean(this.state.overview?.evidence.some((row) => row.provider === this.deps.provider
        && row.next_product_id === productId && row.status === "authorized" && !row.cancel_at_period_end)) };
    this.noticeEnabled = true;
    this.update({ phase: "store", productId, planName: plan?.plan_name ?? null, busy: true,
      message: `Esperando la confirmación de ${this.deps.provider === "apple_app_store" ? "Apple" : "Google Play"}…`, error: null });
    return true;
  }
  storeFailed(message: string | null): void {
    // A late store error must never erase an accepted/verifying transaction.
    if (this.state.phase !== "store") return;
    this.requestedGoal = null;
    this.action = null;
    this.clearMessages();
    this.update({ phase: "idle", busy: false, message: null, error: message });
  }
  clearMessages(): void {
    this.noticeEnabled = false;
    this.update({ message: null, error: null });
  }
  awaitingApproval(): void {
    if (this.state.phase !== "store") return;
    this.requestedGoal = null;
    this.update({ phase: "idle", busy: false,
      message: "La tienda aún no entregó una transacción nueva. Si solicitaste un cambio de modalidad o aprobación, revisa su estado en la tienda." });
  }
  private applySnapshot(overview: SubscriptionData, entitlements: EntitlementsData): void {
    this.update({ overview, entitlements, refreshError: null });
    if (this.state.phase === "active" && entitlements.plan_name !== this.state.planName
      || this.state.phase === "scheduled" && !overview.evidence.some((item) =>
        item.provider === this.deps.provider && item.next_product_id === this.state.productId && item.status === "authorized" && !item.cancel_at_period_end)) {
      this.update({ phase: "idle", message: null, planName: null, productId: "" });
    }
  }
  async reconcile(storeRequestCompleted = false): Promise<void> {
    if (storeRequestCompleted && this.action) this.action.sheetCompleted = true;
    if (!this.alive || this.deps.provider !== "apple_app_store") return this.refresh();
    if (this.reconciliation) return this.reconciliation;
    // Reconciliation and receipt acceptance share the same write queue. A slow
    // pre-purchase reconciliation must never overwrite a newer accepted plan.
    const task = this.queue.then(async () => {
      if (!this.alive) return;
      const result = await this.request<SubscriptionData & { entitlements: EntitlementsData }>(
        "/api/v1/subscriptions/apple/reconcile", { method: "POST" },
      );
      if (!this.alive) return;
      this.snapshotVersion += 1;
      this.applySnapshot(result, result.entitlements);
      if (["store", "pending", "activating"].includes(this.state.phase) && this.confirmBenefits() && this.queued === 0) {
        this.update({ busy: false });
      }
    });
    this.queue = task.catch(() => undefined);
    this.reconciliation = task;
    try { await task; } finally { if (this.reconciliation === task) this.reconciliation = null; }
  }
  async refresh(): Promise<void> {
    if (!this.alive) return;
    if (this.read) return this.read;
    const snapshotVersion = this.snapshotVersion;
    const task = (async () => {
      const snapshot = new AbortController();
      try {
        const [overview, entitlements] = await Promise.all([
          this.request<SubscriptionData>("/api/v1/subscriptions", { cache: "no-store", signal: snapshot.signal }),
          this.request<EntitlementsData>("/api/v1/entitlements", { cache: "no-store", signal: snapshot.signal }),
        ]);
        if (!this.alive || snapshotVersion !== this.snapshotVersion) return;
        this.applySnapshot(overview, entitlements);
        if (["pending", "activating"].includes(this.state.phase)) this.confirmBenefits();
      } catch (error) {
        if (this.alive && snapshotVersion === this.snapshotVersion) this.update({ refreshError: this.deps.errorMessage(error) });
        throw error;
      } finally { snapshot.abort(); }
    })();
    this.read = task;
    try { await task; } finally { if (this.read === task) this.read = null; }
  }
  submit(purchase: StorePurchase, retry = false, source: "event" | "purchase" | "restore" | "recovery" = "event"): Promise<boolean> {
    if (purchase.purchaseState === "pending" && purchase.productId === this.state.productId) this.awaitingApproval();
    if (this.alive && purchase.purchaseState === "purchased" && !purchase.purchaseToken) {
      this.update({ phase: "pending", busy: false, error: "No pudimos leer el comprobante de la tienda. Usa Restaurar compras para recuperarlo.",
        message: "La tienda entregó una transacción. Aún debemos verificar sus beneficios." });
    }
    if (!this.alive || purchase.purchaseState !== "purchased" || !purchase.purchaseToken) return Promise.resolve(false);
    const key = purchase.id || purchase.purchaseToken;
    const existing = this.transactions.get(key);
    if (existing && (!existing.completed || !retry || existing.finished)) return existing.task;
    // Serialize different receipts; duplicate callbacks share exactly one task.
    const record: TransactionRecord = existing ?? { task: Promise.resolve(false), accepted: false, finished: false, completed: false };
    record.completed = false;
    this.queued += 1;
    let preserveStoreRequest = false;
    const task = this.queue.then(async () => {
      if (!this.alive) return false;
      if (!this.state.overview) await this.refresh();
      if (!this.alive) return false;
      const overview = this.state.overview!;
      if (purchase.appAccountToken && purchase.appAccountToken.toLowerCase() !== overview.app_account_token.toLowerCase()) {
        if (this.state.phase === "store" && this.state.productId === purchase.productId) {
          this.storeFailed("Esta compra pertenece a otra cuenta de My Scoope. Inicia sesión con la cuenta que la realizó para restaurarla.");
        }
        return false;
      }
      const historical = overview.transaction_products?.find((item) => item.provider === this.deps.provider && item.product_id === purchase.productId);
      const pack = overview.credit_packs.find((item) => item.provider === this.deps.provider && item.product_id === purchase.productId)
        ?? (historical?.kind === "credit_pack" ? historical : undefined);
      const plan = overview.products.find((item) => item.provider === this.deps.provider && item.product_id === purchase.productId)
        ?? (historical?.kind === "subscription" ? historical : undefined);
      if (!pack && !plan) throw new Error("La compra no corresponde al catálogo disponible. Reintenta Restaurar compras cuando la tienda esté disponible.");
      const freshRequestedReceipt = (source === "event" || source === "purchase") && this.action?.productId === purchase.productId
        && (purchase.transactionReasonIOS ?? purchase.reasonIOS)?.toLowerCase() !== "renewal"
        && (purchase.transactionDate === undefined ? source === "purchase" : purchase.transactionDate >= this.action.startedAt);
      preserveStoreRequest = this.state.phase === "store" && !freshRequestedReceipt;
      if (freshRequestedReceipt && this.action) this.action.hasReceipt = true;
      else if (!preserveStoreRequest && !(this.action?.hasReceipt && this.requestedGoal === this.action.productId)) this.noticeEnabled = false;
      if (!this.requestedGoal && plan && !preserveStoreRequest) this.requestedGoal = purchase.productId;
      const targetId = preserveStoreRequest ? purchase.productId : this.requestedGoal ?? purchase.productId;
      const targetPlan = overview.products.find((item) => item.provider === this.deps.provider && item.product_id === targetId)
        ?? overview.transaction_products?.find((item) => item.provider === this.deps.provider && item.product_id === targetId && item.kind === "subscription");
      const preservesPlanGoal = Boolean(pack && targetPlan && this.requestedGoal && targetId !== purchase.productId);
      if (!preserveStoreRequest) this.update({ phase: "verifying", busy: true, productId: targetId,
        planName: targetPlan?.plan_name ?? null, error: null, message: "Compra confirmada por la tienda. Estamos verificando tus beneficios…" });
      if (!record.accepted) {
        const store = this.deps.provider === "google_play" ? "google-play" : "apple";
        const suffix = store === "apple" ? "transactions" : "purchases";
        const result = await this.request<SubscriptionData & EntitlementsData & {
          entitlements?: EntitlementsData; purchase_status?: "approved" | "refunded";
          transaction_status?: "current" | "superseded" | "inactive";
        }>(`/api/v1/${pack ? "credit-packs" : "subscriptions"}/${store}/${suffix}`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(store === "apple" ? { signed_transaction: purchase.purchaseToken, product_id: purchase.productId } : { purchase_token: purchase.purchaseToken }),
        });
        record.accepted = true;
        this.snapshotVersion += 1;
        if (!this.alive) return true;
        if (preserveStoreRequest) {
          this.update({ ...(plan ? { overview: result } : {}), entitlements: pack ? result : result.entitlements ?? this.state.entitlements });
          record.phase = pack ? result.purchase_status === "refunded" ? "refunded" : "credited" : "active";
        } else if (pack) {
          this.awaitingCredits = !preservesPlanGoal && result.purchase_status !== "refunded" && result.credit_status !== undefined && result.credit_status !== "ready";
          this.update({ entitlements: result, phase: preservesPlanGoal || this.awaitingCredits ? "activating" : result.purchase_status === "refunded" ? "refunded" : "credited",
            message: preservesPlanGoal ? "Revisamos tu saldo. Aún estamos verificando los beneficios de tu suscripción."
              : result.purchase_status === "refunded" ? "Esta compra fue reembolsada. Revisamos tu saldo actual." : "Compra verificada. Tu saldo de créditos ya está actualizado." });
          if (!preservesPlanGoal && !this.awaitingCredits) this.requestedGoal = null;
          if (this.awaitingCredits || preservesPlanGoal) this.confirmBenefits();
        } else {
          this.update({ overview: result, entitlements: result.entitlements ?? null, phase: "activating" });
          if (!result.entitlements) await this.refresh(); // Compatibility with an older backend.
          if (["superseded", "inactive"].includes(result.transaction_status ?? "") && this.requestedGoal === purchase.productId) {
            this.requestedGoal = null;
            this.update({ phase: "idle", message: `Transacción verificada. El plan vigente es ${this.state.entitlements?.plan_name ?? result.plan_name}.` });
          } else this.confirmBenefits();
        }
        if (!preserveStoreRequest) record.phase = this.state.phase;
      } else {
        // Acceptance stays idempotent, but a prior success can have expired or
        // been refunded while StoreKit still needs to finish this receipt.
        if (!preserveStoreRequest) this.update({ phase: "activating", message: "Compra verificada. Estamos revisando tus beneficios actuales…" });
        await this.refresh();
        if (!preserveStoreRequest && pack && !preservesPlanGoal) {
          this.awaitingCredits = record.phase !== "refunded";
          if (!this.awaitingCredits) {
            this.requestedGoal = null;
            this.update({ phase: "refunded", message: "Esta compra fue reembolsada. Revisamos tu saldo actual." });
          }
        }
        const confirmed = preserveStoreRequest || (pack && record.phase === "refunded" && !preservesPlanGoal) ? true : this.confirmBenefits();
        if (!preserveStoreRequest && !pack && !confirmed && ["active", "scheduled", "idle"].includes(record.phase ?? "") &&
          this.requestedGoal === purchase.productId && (!this.state.entitlements?.credit_status || this.state.entitlements.credit_status === "ready")) {
          this.requestedGoal = null;
          this.update({ phase: "idle", message: `Compra verificada. Tus beneficios actuales corresponden al plan ${this.state.entitlements?.plan_name ?? this.state.overview?.plan_name}.` });
        }
      }
      if (!this.alive) return true;
      try {
        await this.deps.finish(purchase, Boolean(pack));
        record.finished = true;
      } catch { /* The store retains unfinished receipts for explicit recovery. */ }
      this.update({ busy: this.state.phase === "store" ? this.state.busy : false, finishPending: [...this.transactions.values()].some((item) => item.accepted && !item.finished) });
      if (this.state.phase === "activating") void this.watchActivation();
      return true;
    }).catch((error) => {
      if (preserveStoreRequest && this.state.phase === "store") return false;
      const status = error && typeof error === "object" && "status" in error ? Number(error.status) : 0;
      const mismatch = [403, 409, 422].includes(status);
      this.update({ phase: mismatch ? "idle" : "pending", busy: false,
        message: mismatch ? "La transacción no pudo asociarse a la cuenta y producto actuales. Revisa tu cuenta y usa Restaurar compras."
          : "La tienda confirmó una compra. Aún no pudimos completar su verificación; usa Reintentar verificación o Restaurar compras.",
        error: this.deps.errorMessage(error) });
      return false;
    });
    record.task = task;
    void task.finally(() => { record.completed = true; this.queued -= 1; });
    this.transactions.set(key, record);
    this.queue = task;
    return task;
  }
  private confirmBenefits(): boolean {
    const { overview, entitlements, productId, planName } = this.state;
    if (entitlements?.credit_status === "frozen") {
      this.update({ phase: "pending", message: "Los créditos necesitan una revisión del equipo de soporte. Tus compras verificadas están guardadas." });
      return false;
    }
    if (entitlements?.credit_status === "pending_reservation") {
      this.update({ message: "La compra está verificada. Una tarea anterior debe finalizar antes de actualizar tus créditos." });
      return false;
    }
    if (this.awaitingCredits && entitlements) {
      this.awaitingCredits = false;
      this.requestedGoal = null;
      this.update({ phase: "credited", message: "Compra verificada. Tu saldo de créditos ya está actualizado." });
      return true;
    }
    const row = overview?.evidence.find((item) => item.provider === this.deps.provider &&
      (item.product_id === productId || item.next_product_id === productId));
    if (row?.next_product_id === productId && row.product_id !== productId && row.status === "authorized" && !row.cancel_at_period_end) {
      this.requestedGoal = null;
      const renewalDate = row.period_end ? new Date(row.period_end) : null;
      const renewal = renewalDate && !Number.isNaN(renewalDate.getTime())
        ? `el ${renewalDate.toLocaleDateString("es", { day: "numeric", month: "long", year: "numeric" })}`
        : "la próxima renovación";
      this.update({ phase: "scheduled",
        message: `Tu cambio a ${planName ?? "la nueva modalidad"} está programado para ${renewal}. Tus beneficios actuales siguen activos.` });
      return true;
    }
    const providerRows = overview?.evidence.filter((item) => item.provider === this.deps.provider) ?? [];
    if (!this.requestedGoal && overview && entitlements && overview.status !== "active" && overview.status !== "trialing") {
      this.update({ phase: "idle", message: "Compra verificada. Esta suscripción ya no tiene beneficios activos." });
      return true;
    }
    if (overview && entitlements && planName && overview.status === "active" &&
      overview.plan_name.toLowerCase() === entitlements.plan_name.toLowerCase() &&
      ((entitlements.plan_name.toLowerCase() === planName.toLowerCase() && !providerRows.some((item) => item.product_id) && !row) ||
        (row?.product_id === productId && row.status === "authorized"))) {
      this.requestedGoal = null;
      this.update({ phase: "active", planName: entitlements.plan_name,
        message: entitlements.plan_name.toLowerCase() === planName.toLowerCase()
          ? `Tu plan ${planName} ya está activo.` : `Compra verificada. Tus beneficios actuales corresponden al plan ${entitlements.plan_name}.` });
      return true;
    }
    return false;
  }
  private watchActivation(): Promise<void> {
    if (this.activation) return this.activation;
    const task = (async () => {
      for (const delay of activationDelays) {
        await (this.deps.wait ?? wait)(delay, this.lifetime.signal);
        if (!this.alive || this.state.phase !== "activating") return;
        try { await this.refresh(); } catch { /* Retain accepted purchase state during a transient outage. */ }
      }
      if (this.alive && this.state.phase === "activating") this.update({ phase: "pending", busy: false,
        message: "La compra está verificada. Aún no pudimos confirmar los beneficios. Reintenta la verificación; no vuelvas a comprar." });
    })();
    this.activation = task;
    void task.finally(() => { if (this.activation === task) this.activation = null; });
    return task;
  }
}
