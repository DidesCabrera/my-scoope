import { ClipboardCheck, MessageCircle } from "lucide-react-native";

import { DistributedTabBar } from "@/components/ui";
import { tokens } from "@/design/tokens";

export type AssistantSection = "chats" | "proposals";

export function AssistantSectionTabs({ activeSection, counts, onChange }: { activeSection: AssistantSection; counts: Record<AssistantSection, number>; onChange(section: AssistantSection): void }) {
  return (
    <DistributedTabBar<AssistantSection>
      accessibilityLabel="Secciones del Asistente AI"
      activeTab={activeSection}
      onChange={onChange}
      tabs={[
        { count: counts.chats, icon: (selected) => <MessageCircle color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />, key: "chats", label: "Chats" },
        { count: counts.proposals, icon: (selected) => <ClipboardCheck color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />, key: "proposals", label: "Propuestas" },
      ]}
    />
  );
}
