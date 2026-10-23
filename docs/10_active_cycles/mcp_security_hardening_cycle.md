# MCP05-MCP08 · Endurecimiento previo a ampliar herramientas

Status: active
Date: 2026-10-22

## Decisión y alcance

Congelar la superficie MVP de tools existentes. Este ciclo protege la identidad,
el permiso comercial y la información que cruza al cliente MCP antes de añadir
capacidades. Se trabaja en la rama `codex/mcp-mvp-validation`, basada en
`staging`. No cambia el Knowledge Center ni habilita el MCP en producción.

## Etapas y criterios de cierre

| Etapa | Cambio | Evidencia de cierre |
| --- | --- | --- |
| MCP05 | Verificación real del bearer en la frontera MCP; scopes efectivos y revocación/PRO en cada solicitud. | Un token inventado, revocado, vencido, de usuario inactivo o sin PRO no inicializa ni descubre tools; un token de lectura no adquiere scope de creación. |
| MCP06 | OAuth vinculado al recurso MCP y PRO fail-closed. | `resource` coincide entre autorización, código, intercambio y token; recurso ausente o distinto se rechaza. La configuración de producción no puede omitir accidentalmente la política PRO. |
| MCP07 | Minimización y control de abuso. | La creación responde con referencia y resumen mínimo; la API impone límites verificables sin registrar bearer ni datos nutricionales. |
| MCP08 | Validación de integración. | Tests negativos y de propiedad, suite MCP y gate backend apropiado; staging smoke solo tras publicar exactamente el commit validado. |

## Límites

- La autenticación del MCP no puede basarse en el prefijo del token ni en scopes
  declarados por el cliente.
- La API sigue siendo autoridad de ownership y de permisos por tool; una
  propuesta sigue pendiente de revisión y no se aplica automáticamente.
- Tokens OAuth de acceso corto y tokens manuales antiguos sin audiencia MCP no
  sirven para iniciar una nueva conexión MCP.
- No usar producción ni datos de terceros como sustituto de pruebas negativas.
- La publicación pública en OpenAI, la migración de clientes heredados y la
  ampliación de tools quedan fuera de este ciclo.
