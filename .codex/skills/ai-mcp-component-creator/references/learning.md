# Componentes AI & MCP — aprendizaje inicial

Revisado: 2026-11-20. Felipe definió este rol; la skill inicia en `pilot`.
Los trabajos anteriores muestran decisiones técnicas, pero no prueban uso de esta
skill antes de su creación.

- El UI System mantiene un contrato semántico y tres implementaciones: Django/CSS
  para web, React Native para iOS/Android y HTML autónomo para MCP Apps. Sus
  galerías sirven para revisar los componentes reales, no para duplicarlos.
  Fuente: `docs/00_current/design/ui_system.md`.
- Las tarjetas MCP de comida, alimento y minuta presentan DTO autorizados del
  backend. La fuente `.source.html` genera el HTML versionado que se entrega al
  host; `npm run check:ui` detecta desincronización. Los URI antiguos pueden
  seguir siendo solicitados por chats existentes. Fuentes:
  `docs/00_current/features/ai_assistant/mcp_meal_card.md` y
  `docs/00_current/features/ai_assistant/mcp_entity_cards.md`.
- La revisión de una tarjeta a 390 px dentro de un navegador de escritorio no
  valida ChatGPT para iPhone. En la vista previa privada, ChatGPT web mostró las
  tarjetas y ChatGPT iOS mostró un rectángulo gris; el MCP de staging sí mostró
  una tarjeta en otro chat nuevo. La causa final no quedó demostrada. Fuente:
  `docs/00_current/features/ai_assistant/mcp_ios_ui_preview_investigation.md`.

Al trabajar en un componente nuevo, sustituye estas notas generales por evidencia
fechada de la superficie, versión, ancho, estado y resultado realmente observados.
