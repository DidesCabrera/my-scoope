# Ciclo de publicación en tiendas móviles

## Estados

Usa una transición explícita y evidencia para avanzar:

1. `discovery`: alcance y candidato todavía no definidos;
2. `scope_approved`: producto, monetización y mercados decididos;
3. `candidate_selected`: versión, build, commit y ambiente identificados;
4. `verification_in_progress`: gates de versión y build en ejecución;
5. `ready_for_review`: paquete completo y recomendación documentada;
6. `submitted`: envío aceptado por la tienda e identificador registrado;
7. `in_review`: revisión externa activa;
8. `changes_required`: rechazo, problema o información adicional requerida;
9. `approved`: tienda aprobó el envío;
10. `release_scheduled` o `released`: liberación elegida o ejecutada;
11. `monitored`: checks posteriores completados;
12. `closed`: ciclo y aprendizajes registrados.

No uses `ready_for_review` cuando un gate aplicable esté `pending`, `revalidate` o
`unverified`, salvo que el gate se haya clasificado explícitamente fuera del
alcance de App Review y Felipe acepte el riesgo restante.

## Identidad del candidato

Registra plataforma, versión comercial, número de build, commit completo, perfil
de build, ambiente/API, identificador de aplicación, identificador EAS/TestFlight,
fecha y alcance aprobado. Un build nuevo invalida únicamente la evidencia ligada
al binario; no borra automáticamente las verificaciones base.

## Informe de readiness de producto

Para la consulta inicial de Felipe, entrega:

1. la decisión evaluada y la identidad del candidato, o la ausencia de candidato;
2. bloqueadores de producto para App Review;
3. tabla completa con `gate`, `estado`, `evidencia reutilizable`, `causa o
   disparador`, `responsable` y `siguiente acción`;
4. dependencias técnicas o de cuenta que impiden el envío, en secciones separadas;
5. la lista mínima de accesos o evidencias necesarias para convertir elementos
   `no verificado` en estados concluyentes;
6. recomendación `no listo`, `listo con condiciones` o `listo para enviar`, con
   confianza y fecha de corte.

No mezcles requisitos de Apple con objetivos comerciales o de lanzamiento. Si un
elemento mejora el lanzamiento pero no bloquea App Review, identifícalo como tal.

## Rechazos y cambios

Conserva el mensaje original de revisión mediante un enlace o identificador,
clasifica la causa, vincula la corrección y registra qué gates fueron afectados.
No reinicies todo el checklist. Después de una corrección, repite los gates
afectados y cualquier flujo de regresión material, y preserva el resto.

## Cierre

Después de liberar, confirma disponibilidad y precio en los storefronts elegidos,
compra o restauración cuando aplique, soporte, señales de errores y la identidad
de la versión observada. Registra aprendizajes y convierte causas repetidas en
mejoras del registro, runbook o automatización.
