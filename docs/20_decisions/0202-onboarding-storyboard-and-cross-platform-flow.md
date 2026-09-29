# 0202 — Storyboard de onboarding y flujo inicial multiplataforma

Status: accepted
Date: 2026-09-28

## Contexto

My Scoope tiene un onboarding web de cuatro pasos y una ficha corporal nativa de
una sola vista. Ambos flujos ya capturan datos útiles, pero no comparten todavía
un relato, una secuencia visual ni una composición equivalente. Las galerías de
UI existentes muestran componentes y algunas composiciones productivas, pero no
permiten revisar cada vista del recorrido inicial sin autenticar usuarios, llamar
APIs o completar el flujo real en un dispositivo.

El objetivo inmediato no es cambiar autenticación, persistencia, compras ni gates.
Es disponer de un storyboard visual que permita decidir orden, contenido y estética
antes de normalizar el comportamiento productivo.

El Target Estimator puede calcular gasto basal con peso, altura, edad y sexo, y
requiere nivel de actividad para estimar gasto de mantenimiento. El objetivo del
usuario permite transformar ese mantenimiento en un target energético inicial.
`training_frequency` forma parte de `NutritionSubjectContext`, pero actualmente no
modifica directamente el cálculo BMR/TDEE. Aun así, es un dato valioso para el
contexto nutricional y debe solicitarse en el nuevo flujo mientras se resuelve su
semántica definitiva en el solver.

La explicación actual tampoco presenta una característica central de My Scoope:
la navegación entre paneles permite pasar de una lectura general a información
nutricional más profunda sin perder sencillez.

## Decisión

### 1. Las galerías alojarán un storyboard visual

Las galerías oficiales serán el espacio de diseño y revisión del recorrido inicial:

- `/app/dev/ui-system/` para Django Web;
- `/dev/ui-gallery` para React Native en iOS y Android.

El storyboard no autenticará, persistirá, comprará ni enviará formularios. Usará
datos fijos y callbacks inocuos. Sus vistas deben reutilizar la presentación
productiva de cada plataforma; no se mantendrán copias visuales independientes.

El storyboard podrá navegarse linealmente y también abrir cualquier vista de forma
directa. Debe hacer visible la posición dentro del recorrido y permitir revisar al
menos un viewport móvil compacto y uno amplio.

### 2. Secuencia canónica para diseño

La secuencia inicial que se diseñará es:

```text
Login
→ Explicación: resultado y propuesta de valor
→ Explicación: estructura nutricional reutilizable
→ Explicación: navegación entre paneles
→ Explicación: asistencia, cálculo y control humano
→ Explicación: seguimiento y evolución
→ Disclosures
→ Objetivo personal
→ Datos personales para estimación
→ Medidas corporales
→ Actividad y frecuencia de entrenamiento
→ Resumen del punto de partida
→ Planes comerciales
→ Home inicial
```

Durante la iteración visual se pueden combinar o retirar vistas explicativas, pero
deben conservarse los conceptos de estructura, navegación entre paneles, control
humano y seguimiento.

Disclosures permanece antes de recopilar la ficha corporal y antes de Home conforme
al contrato vigente de CML08. Cambiar esa posición en el producto requiere una
decisión explícita posterior; la galería puede mostrar alternativas sin convertirlas
en comportamiento productivo.

### 3. Contrato de datos del bloque nutricional

El storyboard solicitará:

```text
goal
birth_date / age_years derivado
sex
height_cm
weight_kg
activity_level
training_frequency
```

La agrupación inicial será:

- objetivo personal;
- datos personales usados por la estimación: fecha de nacimiento y sexo;
- medidas actuales: altura y peso;
- movimiento habitual: nivel de actividad y frecuencia semanal de entrenamiento;
- resumen transparente del punto de partida.

El mantenimiento se basará conceptualmente en peso, altura, edad, sexo y actividad.
El objetivo se usa para el ajuste energético y la referencia inicial de proteína.
`training_frequency` se captura desde el inicio, pero ninguna UI debe afirmar que
altera el mantenimiento hasta que el solver tenga una regla aceptada y probada para
ese dato. Resolver esa regla forma parte del ciclo de normalización.

### 4. Explicación de navegación entre paneles

Una vista explicativa dedicada debe comunicar que My Scoope permite comprender la
alimentación con profundidad y sencillez mediante paneles relacionados. La vista
debe mostrar una transición comprensible entre resumen, calorías, macros,
distribución/asignación y detalle, usando las composiciones reales del sistema de UI
cuando estén disponibles.

No debe presentarse como una lista técnica de tabs. Debe enseñar el modelo mental:
empezar por una lectura simple y profundizar solo cuando el usuario lo necesite.

### 5. Planes comerciales dentro del recorrido

El storyboard mostrará Free, Basic y Pro usando la matriz canónica de la decisión
0201. Free será una vía real y visible para entrar a Home, no una prueba escondida ni
una acción secundaria degradada. La presentación debe explicar diferencias sin
convertirse en una tabla extensa en pantallas pequeñas y debe conservar la política
de propiedad no destructiva de la biblioteca.

La vista comercial del storyboard no procesa compras. La integración con catálogos,
precios localizados, StoreKit, Google Play, Paddle o Mercado Pago queda fuera de esta
primera etapa visual.

### 6. Separación entre presentación y comportamiento

Las rutas productivas conservarán sesión, redirecciones, API, persistencia y compra.
Las vistas compartidas recibirán datos, estado visual y acciones como propiedades o
viewmodels. Esta separación permite que producto y galería rendericen la misma UI
sin inventar sesiones ni producir efectos externos.

## Relación con decisiones anteriores

- Extiende 0186: las galerías continúan usando implementaciones productivas por
  plataforma y no copias aproximadas.
- Evoluciona el onboarding mínimo definido por 0050 y el ciclo ONB00–ONB09 sin
  invalidar su contrato de persistencia actual.
- Mantiene la precedencia de disclosures de CML08.
- Usa la matriz comercial y la política no destructiva de 0201.
- Mantiene la dirección de 0008 hacia un primer Plan diario útil, considerando la
  actualización de 0201 que permite una activación Free determinística sin IA.

## Consecuencias

- Web y Native podrán iterar el relato completo sin depender de cuentas o dispositivos.
- El número final de pantallas no queda congelado antes de la revisión visual.
- La normalización funcional ocurrirá después de aprobar orden, contenido y estética.
- El flujo productivo no debe seguir creciendo como templates o rutas monolíticas;
  primero se extraerán composiciones presentacionales reutilizables.
- `training_frequency` será visible y capturada, pero su influencia matemática deberá
  resolverse y probarse antes de prometerla al usuario.
- Las galerías no sustituyen pruebas funcionales ni validación física posterior; son
  la autoridad para revisar el storyboard y la composición visual de cada plataforma.

## Referencias

- `docs/20_decisions/0186-shared-ui-recipes-and-platform-galleries.md`
- `docs/20_decisions/0201-commercial-launch-plans-and-owned-library.md`
- `docs/20_decisions/0050-onboarding-nutrition-profile-and-subject-context.md`
- `docs/20_decisions/0008-ai-assisted-onboarding-to-first-plan.md`
- `docs/10_active_cycles/onboarding_flow_normalization_cycle.md`
- `notas/application/nutrition_engine/target_estimator.py`
- `notas/application/dto/nutrition_subject_context_dto.py`
