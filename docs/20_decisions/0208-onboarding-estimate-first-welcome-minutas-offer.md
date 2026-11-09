# 0208 — Onboarding hasta estimación y oferta de primeras minutas en Inicio

Status: accepted
Date: 2026-11-09
Supersedes: la obligación de generar y calendarizar minutas antes de completar el onboarding en 0203.

## Contexto

La prueba Android mostró que una meta nutricional válida puede no encontrar dos
minutas compatibles en el catálogo. Como la generación era obligatoria, un fallo
422 dejaba a la persona sin acceso al producto. El recorrido inicial también
pedía preferencias que solo eran necesarias para generar minutas.

## Decisión

- El onboarding Native captura objetivo, identidad, medidas, actividad y frecuencia;
  presenta el mantenimiento y el objetivo calórico estimados; luego permite elegir
  Free, Basic o Pro y entrar a Inicio. La generación no es condición de cierre.
- Las preferencias alimentarias se piden al abrir una invitación independiente y
  gratuita en Inicio: «Primeros pasos: Crea 2 minutas según tus objetivos».
- La invitación permanece si la generación falla o si las propuestas no se guardan.
  Desaparece de Inicio cuando ambas propuestas se aplican como minutas propias.
  Calendarizarlas se ofrece en ese mismo recorrido, pero no bloquea el uso de la app.
- El generador inicial sigue siendo el existente, determinístico y sin cargo de
  créditos. Su optimización y una posible asistencia de IA quedan como mejora
  separada; el mensaje promocional no promete coincidencia perfecta con las metas.
- Un onboarding completado no puede reiniciarse mediante `/onboarding/analyze`;
  las ediciones posteriores usan los endpoints de ficha personal.

## Consecuencias

El estado de la oferta se deriva de las dos propuestas asociadas al perfil y su
estado aplicado, sin guardar una preferencia local ni introducir otra tabla. Las
cuentas que completaron el flujo anterior y ya aplicaron dos propuestas no vuelven
a ver la invitación. Un error del catálogo queda contenido en la pantalla de la
oferta y el usuario puede regresar a Inicio.
