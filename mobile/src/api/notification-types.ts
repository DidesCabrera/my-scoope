export type NotificationItem = {
  kind: "proposal" | "share" | "invitation" | "announcement";
  id: number;
  title: string;
  body: string;
  created_at: string;
  is_read: boolean;
  web_url: string;
  mobile_path: string;
  subject_type?: "comparison" | "daily_plan" | "food" | "meal" | "program" | null;
  comparison_kind?: "foods" | "meals" | "dailyplans" | null;
};

export type NotificationFeed = {
  items: NotificationItem[];
  unread_count: number;
};
