import { Redirect } from "expo-router";

// Existing links and bookmarks now land on the consolidated calendar.
export default function ScheduledPlansRedirect() {
  return <Redirect href="/calendar" />;
}
