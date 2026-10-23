# 0206 — Minuta diaria como vocabulario visible de DailyPlan

Status: accepted
Date: 2026-10-22

## Contexto

`DailyPlan` representa una composición nutricional reutilizable de comidas,
alimentos, porciones, horarios y totales. Después de asignarse a una fecha, el
Calendario conserva un snapshot y lo combina con compromisos, recordatorios y
evidencia de ejecución. La etiqueta visible «Plan diario» confundía la entidad
nutricional con la planificación fechada que posee el Calendario.

El producto también debe poder localizar su interfaz sin traducir nombres
técnicos, contratos o contenido escrito por el usuario.

## Decisión

- En español, `DailyPlan` se presenta como «Minuta diaria» y su plural como
  «Minutas diarias».
- La biblioteca se titula exactamente «Mis minutas diarias».
- En inglés, el equivalente semántico previsto es «Daily meal plan»; no se usa
  una traducción literal de «minuta».
- «Planificación del día» describe el contenedor fechado del Calendario. Allí
  pueden coexistir una minuta, compromisos, recordatorios y ejecución.
- `DailyPlan`, `daily_plan`, `dailyPlan`, `daily-plans`, rutas, esquemas,
  snapshots y eventos analíticos permanecen estables.
- El Asistente acepta «plan diario» como alias de entrada durante la transición,
  pero sus respuestas y acciones visibles usan «minuta diaria».
- Los nombres creados por usuarios no se traducen ni reescriben.
- Las frases se localizan completas; la interfaz no construye traducciones
  concatenando sustantivos aislados.

## Ciclos de ejecución

1. Inventariar web, móvil, backend, Asistente, accesibilidad, notificaciones,
   comparaciones, sharing, onboarding y mensajes comerciales.
2. Establecer vocabulario canónico ES/EN separado de identificadores técnicos.
3. Migrar todas las superficies visibles y conservar aliases de entrada.
4. Ejecutar comprobaciones de terminología y pruebas enfocadas antes de una
   integración más amplia.

## Consecuencias

El cambio visible no requiere migraciones de datos ni rompe contratos. Volver a
«Plan diario» seguiría siendo una modificación de presentación. La localización
runtime completa queda como trabajo separado; este baseline fija el significado
que esa localización deberá preservar.
