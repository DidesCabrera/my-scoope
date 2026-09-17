# Decision 0198: PPK-first daily macro policy

Status: accepted
Date: 2026-09-17

## Context

El estimador ya usaba proteína ligada al peso, pero el contrato conversacional sólo
capturaba gramos y el solver de comidas inventaba 30/40/30 cuando recibía únicamente
calorías. Esto permitía que PPK, porcentajes, gramos y energía fueran instrucciones
paralelas o contradictorias. También confundía un objetivo diario con la distribución
especial que puede solicitarse para una sola comida.

## Decision

Los objetivos diarios se resuelven con una política única del backend:

- la proteína se mantiene ligada al peso y cambia poco ante cambios calóricos;
- 1,6–2,2 g/kg es el rango preferente y 1,0–2,5 g/kg el rango ampliado soportado;
- la grasa diaria queda acotada entre 15% y 35% de la energía, con 25% por defecto;
- los carbohidratos reciben la energía restante y son la variable principal al
  aumentar o reducir calorías;
- una distribución completa indicada por el usuario se respeta sólo si su PPK derivado
  es coherente con peso y energía;
- PPK, distribución y gramos incompatibles no se fusionan silenciosamente: producen un
  error tipado que el asistente debe explicar o aclarar.

El solver de una comida acepta porcentajes explícitos independientes del objetivo
diario. Cuando sólo recibe kcal usa 30/50/20 como heurística visible. Esa heurística no
se guarda como preferencia del usuario.

La periodización por día de entrenamiento/descanso u hora de entrenamiento queda fuera
de esta decisión: el sistema todavía no posee una agenda diaria confiable para aplicarla.

## Consequences

- Cambiar calorías no hace oscilar innecesariamente la proteína; modifica sobre todo
  los carbohidratos.
- Solicitudes como 30/45/25, 30/50/20 y 25/55/20 pueden convertirse a gramos por el
  backend y validarse contra el peso.
- Las propuestas conservan la fuente y la distribución resuelta para revisión.
- Un porcentaje apropiado para una comida no se extrapola automáticamente al día.
- La futura periodización necesitará primero modelar agenda, tipo de día y alcance.
