# Notas para App Review

My Scoope es una app de autogestión nutricional para consumidores que siguen su propio programa. No ofrece diagnóstico ni atención clínica.

## Acceso

La app requiere inicio de sesión. La cuenta dedicada para revisión es `appreview@myscoope.com`, sin autenticación multifactor y sin una suscripción activa, para que App Review pueda recorrer la compra completa en Sandbox. Su contraseña se carga únicamente en App Store Connect y nunca se guarda en este repositorio. La cuenta debe existir y prepararse antes de enviar el build con:

`python manage.py prepare_app_review_demo --login appreview@myscoope.com`

## Recorrido sugerido

1. Iniciar sesión y aceptar la pantalla de transparencia.
2. En **Hoy**, revisar el programa activo, las comidas previstas y sus macros.
3. En **Plan de hoy**, abrir el detalle de una comida y marcar su cumplimiento.
4. Abrir **Registrar peso** y guardar una medición.
5. Abrir **Digitalizar etiqueta nutricional**. La app muestra una vista previa y realiza comprobaciones locales de legibilidad con Apple Vision antes de cualquier envío. El usuario debe activar **Autorizar análisis con OpenAI** antes de poder elegir **Enviar a OpenAI y digitalizar**. Sólo entonces una copia reducida, re-encodedada y sin metadatos se envía temporalmente a OpenAI para extraer los valores. El texto OCR crudo no se conserva y el alimento privado sólo se guarda después de confirmar los valores.
6. Abrir **Mi cuenta**, elegir **Mejorar mi suscripción** y revisar **Suscripciones y Bolsas** para probar compra/restauración en Sandbox. Los precios y periodos proceden de StoreKit; las condiciones de renovación, cancelación, privacidad, términos y reembolsos aparecen en **Información de la suscripción** antes de comprar.
7. Abrir el menú de **Mi cuenta** para acceder al centro de soporte, reportar contenido o un problema y eliminar la cuenta dentro de la app.

## Funciones nativas

- Cámara: se solicita únicamente al abrir la captura de una etiqueta y no usa micrófono. El usuario también puede elegir voluntariamente una fotografía desde su biblioteca mediante el selector del sistema.
- Notificaciones: se solicitan desde Recordatorios y representan horarios del programa calendarizado.
- Sign in with Apple: comparte el mismo flujo OAuth PKCE que los demás accesos.
- Compras: usa StoreKit y muestra el precio localizado por Apple.

## Seguridad y salud

Los cálculos, el OCR y las propuestas asistidas por IA requieren revisión del usuario. La app no reemplaza la atención de un médico o nutricionista. El contenido problemático puede reportarse desde Cuenta.
