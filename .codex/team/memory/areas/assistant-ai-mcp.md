# Asistente AI & MCP — memoria de área

Status: active
Last reviewed: 2026-11-19
Sponsor and final authority: Felipe Dides
Owner role: `ai-application-platform-steward` (ID técnico conservado)

## Objetivo

Diseñar, implementar, evaluar y mantener el asistente interno, sus tools, la
proyección MCP, la orquestación de modelos y el laboratorio de evaluación.
El nombre visible del rol es **Encargado de Asistente AI & MCP**.

## Fuentes y traspasos

La base ejecutable está en el catálogo de capacidades del asistente y
`docs/00_current/features/ai_assistant/evaluation_lab.md`. El rol mantiene
implementación y evidencia de calidad AI. Producto conserva los criterios del
solver y la claridad de arquitectura/contexto; Soporte coordina incidentes y
recibe diagnósticos AI. Una tool nueva no obtiene autoridad sobre datos por su
mera existencia: se respetan las reglas de la aplicación y la aprobación de
Felipe para cambios materiales.

La evaluación del piloto debe comprobar que el rol recupera la batería de
casos, distingue fallos de modelo, tool, solver y datos, y registra una decisión
de avance o reversión sustentada.

El rol está en piloto desde 2026-11-11. La línea base ejecutable de esa fecha
es el catálogo de capacidades del asistente y Evaluation Lab v2; se debe
comprobar su estado actual antes de usarlo como criterio de producción.
