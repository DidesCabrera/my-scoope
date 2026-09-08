import { PanelTabs } from "@/components/ui";

export type AssistantSection = "chats" | "proposals";

const sections = [
  { key: "chats" as const, label: "Chats" },
  { key: "proposals" as const, label: "Propuestas" },
];

export function AssistantSectionTabs({ activeSection, counts, onChange }: { activeSection: AssistantSection; counts: Record<AssistantSection, number>; onChange(section: AssistantSection): void }) {
  return (
    <PanelTabs
      accessibilityLabel="Secciones del Asistente AI"
      activeTab={activeSection}
      onChange={onChange}
      tabs={sections.map((section) => ({ ...section, count: counts[section.key] }))}
    />
  );
}
