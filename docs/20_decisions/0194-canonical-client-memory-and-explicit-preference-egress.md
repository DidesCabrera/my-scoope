# 0194 — Canonical client memory and explicit preference egress

Date: 2026-09-16
Status: accepted

## Decision

AI Assistant profile, preference and proposal drafts use one canonical provider/tool
contract owned by `ai_assistant.domain.client_memory`. Product adapters may map legacy
storage fields into it, but context builders and tools must not expose competing names.

Approved food and meal preferences persist in a user-owned nutrition preference object
only after a trusted UI approval event. The provider cannot call the commit tool.

Approved preferences are not automatically copied into every external-LLM request.
They are read through a controlled capability when the user asks to use saved
preferences or the active product interaction otherwise makes that intent explicit.
This prevents silent egress of sensitive facts such as allergies while retaining useful
cross-chat memory.

## Consequences

- Context/tool drift becomes a contract-test failure.
- Preference drafts can survive across chats after approval.
- A new chat does not imply blanket consent to send all stored preferences externally.
- Product UX must make temporary versus persisted provenance visible.
- Real-provider validation remains mandatory for behavioral closure.

