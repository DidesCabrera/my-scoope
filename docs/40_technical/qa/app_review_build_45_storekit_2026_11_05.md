# Evidencia StoreKit de App Review — build 45

Status: bloqueo de localización de precios cerrado para preparar el siguiente candidato; ciclo de compra y producción pendientes
Fecha: 2026-11-05, America/Santiago
Build observada: My Scoope `1.0.0 (45)`
Distribución: enlace público de TestFlight externo

## Decisión habilitada

La evidencia permite retirar el fallo USD/CLP como bloqueo específico para
preparar y enviar un nuevo candidato a App Review. No garantiza aprobación por
otros motivos y no sustituye las comprobaciones de onboarding, catálogo
productivo, compra, restore, lifecycle, notificaciones, conciliación ni cobro
real.

No se recomienda elevar el iOS mínimo de My Scoope únicamente por este incidente.
La próxima build sigue siendo una decisión separada y requiere las correcciones,
identidad de release y autorización habituales.

## Matriz observada

| Variable | Prueba afectada | Prueba corregida |
| --- | --- | --- |
| Dispositivo | iPhone 17 | El mismo iPhone 17 |
| Distribución | TestFlight externo público | La misma instalación y build de TestFlight |
| App | My Scoope `1.0.0 (45)` | My Scoope `1.0.0 (45)` |
| Sistema | iOS 27.0 | iOS 27.2 después de actualizar el dispositivo |
| Resultado visible | Ofertas pagadas no disponibles; diagnóstico previo devolvió metadata USD incompatible con CHL/CLP | Basic mensual CLP 3.990, Basic anual CLP 34.990, Pro mensual CLP 6.990 y Pro anual CLP 59.990 |

El cambio de sistema también reinició el dispositivo y refrescó estado local de
StoreKit. Por eso esta comparación no aísla por sí sola si el resultado proviene
del binario de iOS 27.2 o de la renovación de sesión/caché. Esa incertidumbre no
cambia la decisión de App Review porque Apple DTS delimitó el defecto al entorno
TestFlight y señaló iOS 27.2 como versión corregida.

## Confirmación de Apple

En el hilo DTS Case-ID `23269821`, Apple respondió el 5 de noviembre de 2026 que:

- el problema debería estar resuelto en iOS 27.2;
- el reporte debe actualizarse si vuelve a ocurrir en esa versión;
- el problema ocurre en TestFlight;
- DTS no puede comprometer fecha ni garantía general de corrección de bugs.

La evidencia positiva y las capturas sanitizadas también se añadieron a
Feedback Assistant `FB25202463`. El número de teléfono, serie e IMEI de la
captura de versión fueron ocultados antes de compartirla.

## Cierre y límites

Se considera cerrado únicamente este gate:

- [x] StoreKit entrega y la app presenta los cuatro precios de suscripción en CLP
  en la build externa 45 sobre iOS 27.2, con confirmación de DTS de que el fallo
  observado pertenece a TestFlight.

Permanecen fuera de este cierre:

- [ ] generar y validar el candidato siguiente sobre un commit exacto;
- [ ] comprobar que onboarding y los catálogos productivos permiten completar el
  recorrido del revisor;
- [ ] ejecutar compra, cancelación, restore y reconciliación sandbox en el
  candidato que se enviará;
- [ ] obtener aprobación de App Review;
- [ ] realizar smoke productivo y una compra real controlada después de publicar.

La prueba anterior de App Review que no superó onboarding se mantiene como un
incidente separado. La falta de minutas/comidas en producción es una hipótesis
plausible, pero este documento no la declara causa confirmada sin evidencia del
reporte de revisión y del estado productivo de ese momento.
