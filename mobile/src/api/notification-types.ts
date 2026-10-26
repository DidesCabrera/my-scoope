export type NotificationItem = {
  kind: "proposal" | "share" | "invitation" | "announcement";
  id: number;
  title: string;
  body: string;
  created_at: string;
  is_read: boolean;
  web_url: string;
  mobile_path: string;
};

export type NotificationFeed = {
  items: NotificationItem[];
  unread_count: number;
};
