# Recorrido móvil de la persona usuaria

Status: human_reference
Date: 2026-10-28
Audience: usuarios staff humanos de producto, soporte, operaciones y desarrollo
Role: human_reference
Authority: non_authoritative
Update-Policy: explicit_user_request_only

> Orientación humana sobre el viaje actual. No sustituye el contrato de API, las reglas de sesión ni
> la documentación de publicación móvil.

## Propósito

La app móvil está orientada primero a personas que gestionan su propia nutrición para pérdida de
grasa, ganancia muscular o recomposición. No presupone un workspace de nutricionista como requisito
del viaje principal.

## Recorrido actual

1. **Ingreso y disclosures:** autenticación, retorno OAuth, condiciones y uso responsable.
2. **Onboarding:** contexto personal y nutricional necesario para orientar la experiencia.
3. **Biblioteca:** alimentos, comidas, planes y programas propios y reutilizables.
4. **Asistente AI:** conversaciones y propuestas revisables dentro de una sección común.
5. **Calendario:** planes por fecha, compromisos, ejecución cotidiana y progreso.
6. **Herramientas:** captura de etiquetas, comparaciones, compartir, Inbox y registros personales.
7. **Cuenta:** créditos, suscripción, restauración, soporte y eliminación de cuenta.

## Ideas clave para soporte

- La sesión móvil usa un cliente público y credenciales protegidas del dispositivo; nunca contiene
  un secreto OAuth embebido.
- La captura de etiquetas procesa la imagen para extraer datos, muestra incertidumbre y persiste solo
  lo confirmado como alimento privado. No publica directamente en Food Catalog.
- Los selectores de fecha, hora y medidas deben confirmar valores estables; una interacción en curso
  no debería mutar repetidamente la pantalla que contiene el selector.
- Los detalles nutricionales pueden mostrar energía, macros y nutrientes extendidos cuando existen;
  ausencia de un valor no significa cero.
- Las notificaciones son una ayuda, no la autoridad de la planificación. El calendario conserva la
  agenda aunque el permiso de notificaciones esté negado.
- Staging y producción son entornos separados. Simulator, TestFlight y tiendas pueden mostrar datos,
  precios o builds diferentes según el entorno y la versión instalada.

## Cuando una pantalla no coincide con lo esperado

Verificar primero la build instalada, el entorno al que apunta, el usuario autenticado y si la vista
representa una plantilla, una propuesta o un snapshot. Después revisar conectividad y estado del
backend. Solo entonces clasificarlo como defecto visual, contrato móvil, dato o incidente de servicio.

## Referencias

- [Calendario, planificación y progreso](calendar_and_progress.md)
- [Compartir y comparar](sharing_and_comparisons.md)
- [Pagos y salud de la beta](billing_and_beta.md)
