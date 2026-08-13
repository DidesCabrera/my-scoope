# MSOS — My Scoope Operating System

MSOS es la fuente estratégica y fundacional versionada de My Scoope. Reúne la identidad, estrategia, áreas, preguntas ejecutivas, decisiones, riesgos, prioridades y ciclos con los que se construye y dirige la empresa.

La primera versión, **MSOS00**, es deliberadamente simple y de solo lectura. La vista interna `/msos/` presenta el contenido estructurado de `msos_data.json`; no utiliza modelos ni base de datos y no permite edición desde el navegador.

## Fuente de verdad

- `msos_data.json` contiene los datos visibles en la vista.
- Los cambios deben revisarse y versionarse junto al código.
- La vista no debe duplicar ni reinterpretar el contenido.
- Este directorio no forma parte del Knowledge Center: es una fuente estratégica de empresa.

## Evolución

MSOS crece por ciclos pequeños y verificables, de la misma forma que el producto. MSOS00 establece la arquitectura; los ciclos siguientes profundizarán lanzamiento, identidad, producto, marketing, finanzas, legal, comercial, operaciones y dirección ejecutiva.

## Modelo de información

MSOS separa tres tipos de información para evitar mezclar definiciones duraderas con ejecución:

- **Definiciones:** Identidad establece quién es My Scoope; MKT define para quién existe, qué valor entrega y cómo se diferencia.
- **Dirección temporal:** Estrategia jerarquiza la meta anual, el trimestre actual, el siguiente y los proyectos del roadmap.
- **Operación:** Departamentos conserva responsabilidades y prioridades por área; CEO Dashboard concentra la revisión diaria.

Los departamentos son capacidades permanentes de la empresa. Los proyectos son esfuerzos temporales, pueden involucrar varias áreas y contienen sus propios objetivos e hitos.

Las cards del CEO Dashboard y del roadmap son puntos de entrada, no contenedores de toda la conversación. Cada una abre una página propia con una estructura adaptable al asunto: puede reunir contexto, preguntas, criterios, riesgos, evidencia, conclusiones, objetivos o hitos según sea necesario. El enlace de retorno conserva el tab desde el que se ingresó.

Dentro de una página, las cards de frentes mantienen únicamente una síntesis visible. Cada frente recibe una página independiente desde su creación para conservar contexto, criterios provisionales, decisiones pequeñas y preguntas de reflexión sin perder la vista general de readiness.
