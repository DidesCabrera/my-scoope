type SubscriptionCreditPack = {
  product_id: string;
  provider: "apple_app_store" | "google_play" | string;
  credits: number;
  amount_minor: number;
  currency: string;
};

export type SubscriptionData = {
  eligible: boolean;
  purchases_enabled: boolean;
  app_account_token: string;
  google_obfuscated_account_id: string;
  plan_name: string;
  status: string;
  products: {
    product_id: string;
    provider: "apple_app_store" | "google_play" | string;
    base_plan_id: string;
    plan_name: string;
    interval: "month" | "year" | string;
  }[];
  credit_packs: SubscriptionCreditPack[];
  can_buy_credit_packs: boolean;
  evidence: {
    provider: string;
    status: string;
    period_end: string | null;
  }[];
  duplicate_active_providers: boolean;
};

export type EntitlementsData = {
  plan_name: string;
  plan_slug: string;
  subscription_status: string;
  period: string;
  available_credits: number;
  reserved_credits: number;
  monthly_credit_limit: number;
  daily_credit_limit: number;
  included_monthly_credits: number;
  purchased_credits: number;
  workspace_limits: Record<string, number | null>;
  workspace_usage: Record<string, number>;
};
