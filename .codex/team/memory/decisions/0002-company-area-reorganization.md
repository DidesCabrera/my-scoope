# Decision 0002: Reorganización de áreas del equipo AI

Status: accepted
Date: 2026-11-19
Decision owner: Felipe Dides

## Context

El área anterior «Producto y tecnología» reunía producto, asistente AI y
respuesta a incidentes. «Equipo AI» describía capacidad del equipo, pero Felipe
quiere una adscripción operativa de Gestión de Proyectos. También identificó un
rol recurrente para ordenar ramas, PR y checkouts.

## Decision

- Separar Producto, Asistente AI & MCP y Soporte.
- Producto: Nutrition Solver Steward, AI Architecture and Context Steward y
  Mobile Store Release Steward. Arquitectura y Contexto permanece aquí porque
  ayuda a una AI a comprender el código y sus contratos al abordar el proyecto.
- Asistente AI & MCP: rol visible **Encargado de Asistente AI & MCP**; el ID
  técnico `ai-application-platform-steward` se conserva por compatibilidad.
- Soporte: Observability Lead, especialistas de incidentes móviles, backend y
  publicación, e Incident Verifier.
- Renombrar el área Equipo AI a Gestión de Proyectos. Allí se adscriben AI Team
  Capability Steward, Strategic Product Advisor, Parallel Work Coordinator y el
  nuevo Encargado de ramas y checkouts.
- Commercial Strategy Advisor permanece en Comercial y Marketing.

Esta decisión reemplaza la agrupación inicial de áreas de la decisión 0001,
manteniendo el modelo de roles, la autoridad final de Felipe y los traspasos
entre especialidades.

## Consequences

El registro, organigrama, memorias de área y metadatos visibles deben reflejar
esta distribución. Los roles conservan su mandato funcional y los shared skills
siguen disponibles transversalmente. El nuevo rol de ramas inicia como piloto;
su existencia no autoriza descartar trabajo ni alterar checkouts ajenos.

## Evidence that would justify reconsideration

Casos reales en que las nuevas adscripciones dificulten el enrutamiento,
dupliquen autoridad o retrasen la resolución de incidentes o proyectos.
