# Soporte — memoria de área

Status: active
Last reviewed: 2026-11-19
Sponsor and final authority: Felipe Dides
Coordinator: `observability-lead`

## Objetivo

Detectar, correlacionar, priorizar y resolver problemas observados en las
superficies móviles, backend y publicación, con cierre independiente cuando
corresponde. El área usa evidencia de producción y staging; un incidente no se
declara resuelto solo por un cambio de código.

## Roles definidos

- `observability-lead`: triage, prioridad y coordinación.
- `mobile-incident-specialist`: límite React Native, Expo, navegación y dispositivo.
- `backend-incident-specialist`: límite Django, API, datos y servidor.
- `release-incident-specialist`: builds, despliegues, entornos y entrega.
- `incident-verifier`: reproducción y cierre independiente.

El líder delega solo cuando la especialización o verificación separada añade
valor; Felipe puede dirigirse a cualquiera directamente. Producto y Asistente AI
& MCP conservan la propiedad de sus cambios de capacidad y envían a Soporte los
diagnósticos necesarios durante un incidente.

Los cuatro roles de especialista/verificación permanecen en piloto. Su
evaluación debe mostrar casos repetidos con fuentes de evidencia, decisiones y
validación realmente distintas antes de promoverlos.
