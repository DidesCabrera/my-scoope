# 0210 — Vista previa de la card MCP dentro de ChatGPT

Status: accepted for local experimentation; first real-host session passed; revisit when workflow changes
Date: 2026-11-14

## Contexto

La galería web sirve el mismo HTML de la card MCP, pero su iframe usa anchos de
prueba. ChatGPT decide el espacio efectivo del iframe en web, aplicación de
escritorio, panel lateral y móvil. En las capturas comparadas del 14 de noviembre,
la card de ChatGPT desperdicia espacio exterior y dedica más altura al encabezado
que la card web. La galería por sí sola no permite validar esa diferencia.

Publicar cada ajuste visual en `origin/staging`, desplegar el MCP y refrescar el
plugin prolonga la iteración y mezcla experimentos de diseño con la línea de
integración.

## Decisión

Usar un servidor MCP de desarrollo independiente que sirva la card actual con
datos sintéticos. Se conecta a un plugin privado de desarrollo en ChatGPT mediante
un túnel privado. El servidor ofrece una herramienta visible que muestra la comida
de ejemplo y otra herramienta exclusiva de la app que devuelve el CSS editable.
La card consulta esta última periódicamente y aplica los cambios de estilo en el
iframe existente. Así el ajuste de dimensiones se observa en el host real sin
publicar en staging. El URI del recurso cambia al iniciar el servidor para evitar
que una versión antigua de HTML quede en caché.

La galería y el smoke local siguen siendo comprobaciones rápidas de estructura y
anchos conocidos. La conversación real es la autoridad para el espacio disponible,
escalado y aspecto final. Se deben revisar por separado web, escritorio, panel
lateral y móvil. Antes de integrar la card se ejecutan los controles normales del
repositorio y una comprobación final en ChatGPT.

## Alcance y límites

- El servidor de desarrollo no consulta My Scoope, no usa credenciales de usuario
  y solo entrega datos ficticios. No sustituye la autorización ni las pruebas del
  MCP de staging.
- La recarga en vivo cubre CSS de `meal_card_v5.source.html`. Cambios de HTML,
  JavaScript, contrato de datos o tokens generados requieren regenerar el recurso,
  reiniciar el servidor y refrescar la conexión de desarrollo.
- El túnel y el plugin de desarrollo son temporales. No se usan para producción.
- Esta es una decisión de flujo de trabajo para la iteración actual, no una
  prohibición de explorar una galería calibrada, otro túnel, un emulador mejor o
  una futura integración de recarga distinta. Se revisará tras medir velocidad,
  fidelidad y estabilidad en la primera sesión dentro de ChatGPT.

## Verificación

El 14 de noviembre de 2026, el plugin personal **My Scoope Card Preview** se
conectó mediante un Secure MCP Tunnel privado. En una conversación real de
ChatGPT, `preview_meal_card` mostró la card con cuatro alimentos ficticios. Un
cambio temporal del borde superior de magenta a rojo en
`meal_card_v5.source.html` apareció en el mismo iframe sin recargar el chat,
reiniciar el servidor ni publicar en staging. Al restaurar el archivo, el borde
volvió a magenta. La prueba visual se hizo en el panel estrecho del navegador
integrado; falta registrar medidas de la superficie web de escritorio y de la
aplicación de escritorio al iterar sus dimensiones.

Referencias: [MCP Apps](https://apps.extensions.modelcontextprotocol.io/api/),
[conexión y pruebas en ChatGPT](https://developers.openai.com/plugins/deploy/connect-chatgpt).
