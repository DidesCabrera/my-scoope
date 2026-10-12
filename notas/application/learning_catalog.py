"""User-facing educational catalog, independent from internal documentation."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LearningSection:
    heading: str
    body: str


@dataclass(frozen=True)
class LearningArticle:
    slug: str
    title: str
    summary: str
    icon: str
    sections: tuple[LearningSection, ...]
    takeaway: str
    source_label: str = ""
    source_url: str = ""


NUTRITION_FOUNDATIONS = (
    LearningArticle(
        slug="alimentacion-saludable",
        title="Qué significa comer saludable",
        summary="Adecuación, equilibrio, moderación y diversidad como principios generales.",
        icon="heart-pulse",
        sections=(
            LearningSection("No existe una única dieta perfecta", "Una alimentación saludable puede tomar formas muy distintas. Debe adaptarse a la edad, el nivel de actividad, la cultura, la disponibilidad de alimentos, las preferencias y la situación de salud de cada persona. Por eso, copiar un menú sin considerar su contexto no garantiza que sea adecuado ni sostenible."),
            LearningSection("Cuatro principios para orientarse", "Adecuación significa cubrir energía y nutrientes sin quedar sistemáticamente por debajo de las necesidades. Equilibrio relaciona lo que se consume con el gasto y combina los distintos nutrientes. Moderación limita los excesos frecuentes, especialmente de sal, azúcares libres y grasas poco saludables. Diversidad incorpora alimentos variados dentro de cada grupo y entre grupos."),
            LearningSection("Importa el patrón completo", "Un alimento aislado rara vez define la calidad de toda la alimentación. Conviene observar qué se come habitualmente, en qué cantidades y con qué frecuencia. Una base de alimentos variados y mínimamente procesados —como verduras, frutas, legumbres, cereales integrales y fuentes apropiadas de proteína— deja espacio para elecciones ocasionales sin convertirlas en el centro del patrón."),
            LearningSection("La alimentación también debe ser practicable", "Un plan puede verse correcto en números y aun así ser difícil de sostener por costo, tiempo, disponibilidad o preferencias. La mejor organización es la que permite repetir conductas útiles con flexibilidad. Si existen alergias, enfermedades, embarazo u otras necesidades clínicas, la orientación general no reemplaza una evaluación profesional individual."),
        ),
        takeaway="Evalúa el patrón habitual, su variedad y su sostenibilidad; no juzgues toda la alimentación por una comida o un alimento aislado.",
        source_label="OMS · Alimentación saludable",
        source_url="https://www.who.int/es/news-room/fact-sheets/detail/healthy-diet",
    ),
    LearningArticle(
        slug="energia-y-calorias",
        title="Energía, calorías y balance",
        summary="Cómo se relacionan la energía ingerida, el gasto y los objetivos corporales.",
        icon="flame",
        sections=(
            LearningSection("Qué representa una caloría", "La energía de los alimentos suele expresarse en kilocalorías, aunque en el uso cotidiano se diga simplemente “calorías”. El cuerpo utiliza esa energía para mantener funciones vitales, regular la temperatura, digerir, moverse, entrenar y recuperarse. Las calorías describen una cantidad de energía; por sí solas no describen la calidad nutricional del alimento."),
            LearningSection("Ingesta y gasto cambian cada día", "El balance energético compara la energía consumida con la que el cuerpo utiliza. No es una cuenta perfectamente cerrada en cada jornada: tanto la ingesta como el gasto varían, y el organismo también se adapta. Para interpretar cambios corporales resulta más útil observar el promedio y la tendencia de varias semanas que exigir coincidencia exacta todos los días."),
            LearningSection("Las estimaciones son un punto de partida", "Edad, sexo usado para el cálculo, altura, peso y actividad permiten estimar necesidades energéticas. La fórmula entrega una referencia inicial, no una medición directa del metabolismo. Sueño, entrenamiento, movimiento cotidiano, estado de salud y precisión del registro pueden hacer que la respuesta real sea diferente."),
            LearningSection("Cómo ajustar con criterio", "Primero procura registrar y ejecutar el plan con una consistencia razonable. Después revisa tendencias de peso, hambre, energía, recuperación y rendimiento. Si el resultado se aleja del objetivo de forma sostenida, un ajuste pequeño y evaluado durante suficiente tiempo suele aportar más información que varios cambios grandes y simultáneos."),
        ),
        takeaway="Usa la estimación calórica como una referencia revisable y decide los ajustes a partir de tendencias, no de un único día.",
        source_label="EFSA · Valores dietéticos de referencia",
        source_url="https://www.efsa.europa.eu/en/topics/topic/dietary-reference-values",
    ),
    LearningArticle(
        slug="macronutrientes",
        title="Proteínas, carbohidratos y grasas",
        summary="El papel de los tres macronutrientes que My Scoope muestra en comidas y planes.",
        icon="chart-no-axes-column-increasing",
        sections=(
            LearningSection("Qué son los macronutrientes", "Proteínas, carbohidratos y grasas son nutrientes que el cuerpo necesita en cantidades relativamente grandes. Los tres pueden contribuir a la energía total, pero no son intercambiables: cumplen funciones distintas. My Scoope los muestra en gramos y también dentro del total del plan para que puedas revisar cantidad y distribución."),
            LearningSection("Proteínas", "Las proteínas aportan aminoácidos utilizados en tejidos, enzimas y otras estructuras del organismo. La cantidad apropiada depende de la persona y su contexto, y no se interpreta bien mirando una sola comida. También conviene variar las fuentes y considerar el resto del alimento, no únicamente sus gramos de proteína."),
            LearningSection("Carbohidratos y fibra", "Los carbohidratos son una fuente importante de energía, especialmente relevante para actividades de mayor intensidad. No todos aportan lo mismo: legumbres, frutas, verduras y cereales integrales pueden sumar fibra y micronutrientes, mientras que los azúcares libres conviene limitarlos. La fibra forma parte de la calidad del patrón aunque no siempre aparezca en el resumen principal de macros."),
            LearningSection("Grasas y contexto", "Las grasas participan en membranas celulares, transporte de vitaminas y aporte de ácidos grasos esenciales. Por su densidad energética, pequeños cambios de cantidad pueden modificar bastante las calorías del plan. Además del total, importa priorizar fuentes de grasas insaturadas y limitar grasas trans y el exceso de grasas saturadas."),
        ),
        takeaway="Usa los macros para entender la composición, pero evalúa también las fuentes, la fibra, la variedad y el contexto del plan.",
        source_label="OMS · Alimentación saludable",
        source_url="https://www.who.int/en/news-room/fact-sheets/detail/healthy-diet",
    ),
    LearningArticle(
        slug="proteina-por-kilo",
        title="Proteína por kilogramo (PPK)",
        summary="Por qué My Scoope relaciona la proteína con el peso de la ficha personal.",
        icon="badge-info",
        sections=(
            LearningSection("Una medida relativa", "La proteína por kilogramo, o PPK, divide los gramos diarios de proteína por el peso de referencia expresado en kilogramos. Por ejemplo, 120 g de proteína y 80 kg de peso equivalen a 1,5 g/kg. La medida permite comparar el aporte con el tamaño corporal mejor que los gramos totales por sí solos."),
            LearningSection("El peso de referencia cambia el resultado", "El PPK depende de dos datos: proteína total y peso de referencia. Si el peso guardado en la ficha cambia, el PPK visible también puede cambiar aunque las comidas conserven exactamente la misma proteína. Del mismo modo, dos personas que comen los mismos gramos pueden obtener valores PPK diferentes."),
            LearningSection("Cómo leerlo dentro de My Scoope", "Comprueba primero que la ficha personal use un peso vigente y representativo. Luego revisa juntos los gramos totales, el PPK y la distribución de proteína durante el día. Un valor relativo facilita la interpretación, pero no demuestra por sí solo que la selección de alimentos o el plan completo sean adecuados."),
            LearningSection("No es una meta universal", "Las necesidades varían según edad, actividad, objetivo, estado de salud y otras circunstancias. Los valores de referencia poblacionales ayudan a orientar evaluaciones, pero no sustituyen una recomendación individual. Ante enfermedad renal, embarazo, necesidades clínicas u objetivos deportivos específicos, corresponde consultar a un profesional competente."),
        ),
        takeaway="Mantén actualizado el peso de referencia y lee siempre el PPK junto con los gramos totales y el contexto personal.",
        source_label="EFSA · Valores dietéticos de referencia",
        source_url="https://www.efsa.europa.eu/en/topics/topic/dietary-reference-values",
    ),
    LearningArticle(
        slug="calidad-variedad-y-fibra",
        title="Calidad, variedad y fibra",
        summary="Por qué dos planes con macros parecidos pueden tener distinta calidad alimentaria.",
        icon="salad",
        sections=(
            LearningSection("Dos planes parecidos pueden ser distintos", "Calorías y macronutrientes permiten comparar cantidades, pero no muestran por completo fibra, vitaminas, minerales, grado de procesamiento ni variedad. Dos planes con números similares pueden tener una calidad alimentaria diferente. Por eso, alcanzar los macros no es el final de la revisión."),
            LearningSection("Qué aporta la variedad", "Frutas, verduras, legumbres, cereales integrales, frutos secos y fuentes variadas de proteína aportan combinaciones diferentes de nutrientes. Rotar alimentos dentro de un patrón coherente reduce la dependencia de una selección muy estrecha y aumenta la probabilidad de cubrir necesidades de vitaminas y minerales."),
            LearningSection("La fibra como señal útil", "La fibra está presente principalmente en alimentos vegetales como legumbres, frutas, verduras, frutos secos y granos integrales. Contribuye al funcionamiento digestivo y suele acompañar alimentos de buena densidad nutricional. Aumentarla de golpe puede causar molestias, por lo que conviene hacerlo gradualmente y cuidar la hidratación."),
            LearningSection("Una revisión práctica", "Al mirar un día o una semana, pregunta si aparecen distintos colores y tipos de vegetales, fuentes de fibra y proteínas variadas. Revisa también qué alimentos dominan por frecuencia. No necesitas maximizar la variedad en cada comida: importa que el patrón acumulado sea diverso y realizable."),
        ),
        takeaway="Después de revisar calorías y macros, comprueba variedad, fuentes de fibra y calidad del patrón a lo largo de la semana.",
        source_label="OMS · Alimentación saludable",
        source_url="https://www.who.int/es/news-room/fact-sheets/detail/healthy-diet",
    ),
    LearningArticle(
        slug="seguimiento-y-ajustes",
        title="Seguimiento y ajustes",
        summary="Cómo interpretar cambios de peso y adaptar un plan sin reaccionar a un solo dato.",
        icon="line-chart",
        sections=(
            LearningSection("Una medición no define una tendencia", "El peso corporal puede variar por hidratación, sodio, carbohidratos almacenados, contenido digestivo y horario de medición. Un cambio puntual no equivale necesariamente a ganancia o pérdida de tejido. Varias mediciones tomadas en condiciones parecidas ofrecen una señal más útil que un único número."),
            LearningSection("Comparar periodos equivalentes", "Para reducir ruido, procura usar una rutina de medición consistente y compara promedios o tendencias de varias semanas. Considera también el ciclo menstrual, viajes, enfermedad y cambios de entrenamiento cuando correspondan. La velocidad esperada depende del objetivo y del punto de partida."),
            LearningSection("No todo se resume en el peso", "Adherencia, hambre, energía, digestión, sueño, recuperación, rendimiento y medidas corporales pueden aportar contexto. Una tendencia de peso compatible con el objetivo no compensa un plan que resulte inviable o produzca síntomas relevantes. Registra las señales que realmente ayuden a tomar decisiones."),
            LearningSection("Cambiar una cosa y volver a observar", "Antes de ajustar, confirma que el plan se ejecutó de manera razonablemente consistente. Si hace falta un cambio, modifica una variable con prudencia y dale tiempo suficiente para evaluar su efecto. Cambiar calorías, actividad y distribución a la vez dificulta saber qué produjo el resultado."),
        ),
        takeaway="Decide a partir de tendencias y contexto; realiza ajustes graduales y vuelve a observar antes de cambiar de nuevo.",
    ),
)


SYSTEM_MANUALS = (
    LearningArticle(
        slug="fichas-personales",
        title="Fichas personales",
        summary="Mantén actualizados los datos que alimentan cálculos, objetivos y planes.",
        icon="files",
        sections=(
            LearningSection("Qué información reúnen", "Fichas personales concentra los datos que describen tu contexto: información corporal, objetivo y actividad, preferencias alimentarias y registros de progreso. Cada bloque cumple una función distinta. Revisarlos juntos ayuda a detectar datos antiguos o incompletos antes de crear o evaluar una planificación."),
            LearningSection("Por qué conviene mantenerlas al día", "Los datos guardados pueden utilizarse para estimaciones, indicadores y futuras propuestas. Si cambian tu peso, objetivo, actividad o preferencias, actualiza la ficha correspondiente antes de pedir un nuevo cálculo. Editar la ficha mejora el contexto futuro, pero no significa que todo elemento creado anteriormente se reescriba automáticamente."),
            LearningSection("Cómo revisar y editar", "Abre Fichas personales desde la navegación principal, entra en la ficha que necesitas y lee los valores actuales antes de pulsar “Editar información”. Modifica solamente los campos que puedas confirmar, guarda y vuelve al detalle para comprobar el resultado. Si un campo queda vacío, no asumas que el sistema conoce ese dato por otra vía."),
            LearningSection("Buenas prácticas", "Usa valores actuales y unidades correctas, y evita cambiar datos sólo para forzar un resultado deseado. Revisa especialmente el peso de referencia cuando interpretes proteína por kilogramo y la actividad cuando observes estimaciones energéticas. Las condiciones clínicas y recomendaciones profesionales deben registrarse y aplicarse con el criterio correspondiente."),
        ),
        takeaway="Revisa la ficha antes de generar o ajustar planes y confirma el detalle después de guardar cualquier cambio.",
    ),
    LearningArticle(
        slug="bibliotecas",
        title="Bibliotecas y jerarquía",
        summary="Entiende cómo se relacionan alimentos, comidas, planes diarios y programas.",
        icon="library-big",
        sections=(
            LearningSection("La jerarquía del sistema", "Los alimentos son la base nutricional. Una comida reúne alimentos con sus cantidades; un plan diario organiza comidas; y un programa distribuye planes diarios entre días y semanas. Entender esta jerarquía permite editar en el nivel correcto y evita confundir un ingrediente con la estructura completa donde se utiliza."),
            LearningSection("Para qué sirven las bibliotecas", "Cada biblioteca reúne elementos de un mismo tipo para que puedas buscarlos, abrir su detalle y reutilizarlos en estructuras mayores. Antes de crear algo nuevo, revisa si ya existe un elemento que puedas aprovechar. Los nombres claros y diferenciables facilitan encontrar la versión correcta más adelante."),
            LearningSection("Editar con contexto", "Antes de modificar un alimento, comida o plan, revisa dónde esperas ver el cambio. Las estructuras ya creadas pueden conservar información propia o requerir una edición separada según el flujo. Después de guardar, vuelve al elemento superior relevante y verifica cantidades, composición y totales en lugar de asumir que toda referencia cambió."),
            LearningSection("Duplicar, compartir e incorporar", "Duplicar resulta útil cuando necesitas una variante sin perder el original. Compartir permite entregar un elemento para que otra persona lo revise, mientras que incorporarlo lo sitúa dentro de una comida, plan o programa. En cada caso, confirma el tipo de elemento, su identidad y su información nutricional antes de continuar."),
        ),
        takeaway="Identifica primero el nivel que quieres cambiar y verifica después el resultado en la estructura donde realmente lo usarás.",
    ),
    LearningArticle(
        slug="programa-activo",
        title="Inicio y programa activo",
        summary="Consulta qué corresponde hoy y recorre la planificación calendarizada.",
        icon="calendar-clock",
        sections=(
            LearningSection("Qué muestra Inicio", "Inicio está pensado para responder qué corresponde hacer hoy. Cuando existe una planificación vigente, prioriza el día actual y sus acciones principales. Úsalo como punto de entrada cotidiano; no necesitas recorrer toda la estructura del programa cada vez que quieras consultar el plan del día."),
            LearningSection("Qué muestra Programa activo", "Programa activo ofrece una vista más amplia de la planificación calendarizada. Desde allí puedes recorrer semanas y días, consultar cómo se distribuyen los planes y entender qué viene después. Es la vista adecuada cuando necesitas contexto, anticipar cambios o revisar la continuidad del programa."),
            LearningSection("Planificado no significa ejecutado", "La estructura indica lo previsto para una fecha, mientras que el seguimiento registra lo que efectivamente ocurrió. Revisa el día correcto antes de marcar acciones o interpretar avances. Si una fecha no tiene un plan asignado, el calendario puede conservar el día sin inventar contenido nutricional."),
            LearningSection("Cómo orientarte", "Empieza en Inicio para actuar sobre el presente. Abre Programa activo cuando necesites revisar otra fecha, entender la semana completa o confirmar qué plan está asociado a cada día. Si lo visible no coincide con lo esperado, comprueba primero el programa activo y la fecha seleccionada."),
        ),
        takeaway="Usa Inicio para el día en curso y Programa activo para revisar la secuencia completa de semanas y fechas.",
    ),
    LearningArticle(
        slug="comparaciones",
        title="Comparaciones",
        summary="Compara alimentos, comidas o planes usando el mismo contexto nutricional.",
        icon="scale",
        sections=(
            LearningSection("Elegir elementos comparables", "Una comparación es más clara cuando enfrenta dos elementos del mismo tipo: alimento con alimento, comida con comida o plan con plan. Confirma nombres, porciones y cantidades antes de interpretar los resultados. Comparar estructuras distintas puede producir diferencias reales, pero difíciles de convertir en una decisión útil."),
            LearningSection("Leer las diferencias", "Observa primero la base de comparación y luego calorías, proteínas, carbohidratos y grasas. En comidas y planes, considera también la composición: un total parecido puede provenir de alimentos muy diferentes. Una cifra mayor no es automáticamente mejor o peor; debe relacionarse con el objetivo de la comparación."),
            LearningSection("Formular una pregunta concreta", "Antes de comparar, define qué quieres decidir: más proteína para una comida, una porción con menos energía, mayor variedad o una alternativa que encaje mejor en el día. Esa pregunta determina qué diferencias importan. Sin un criterio previo, es fácil tratar todos los indicadores como si tuvieran la misma prioridad."),
            LearningSection("Guardar la conclusión correcta", "La comparación aporta evidencia para elegir, pero no modifica los elementos por sí sola. Si decides usar una alternativa, vuelve a la biblioteca o al flujo correspondiente para incorporarla. Revisa después el contexto completo, porque una elección conveniente de manera aislada puede alterar el total de la comida o del día."),
        ),
        takeaway="Define primero la decisión que quieres tomar y usa la comparación como evidencia contextual, no como un ranking universal.",
    ),
    LearningArticle(
        slug="compartidos",
        title="Compartidos",
        summary="Recibe elementos de otros usuarios y decide si incorporarlos a tu biblioteca.",
        icon="user-plus",
        sections=(
            LearningSection("Qué significa recibir un elemento", "Un elemento compartido te permite revisar información creada por otra persona sin incorporarla de inmediato a tu organización. El nombre ayuda a identificarlo, pero no basta para decidir. Abre el detalle y confirma el tipo de elemento, su estructura, cantidades y datos nutricionales disponibles."),
            LearningSection("Revisar antes de guardar", "Comprueba que el contenido corresponda con lo que esperabas recibir y que sus unidades y porciones tengan sentido para tu contexto. En comidas, planes o programas, recorre los niveles internos antes de aceptarlos. Si falta información importante o algo parece inconsistente, consulta a quien lo compartió antes de utilizarlo."),
            LearningSection("Tu biblioteca conserva el control", "Guardar crea un elemento utilizable dentro de tu propio espacio. A partir de ese momento puedes revisarlo y adaptarlo sin editar la biblioteca de quien lo envió. Del mismo modo, los cambios posteriores de la otra persona no deben asumirse como actualizaciones automáticas de lo que ya guardaste."),
            LearningSection("Después de incorporarlo", "Ponle un nombre que puedas reconocer y verifica el detalle guardado en tu biblioteca. Si planeas integrarlo en una estructura mayor, revisa su efecto en los totales y en la organización correspondiente. Recibir contenido facilita la colaboración, pero no reemplaza tu decisión sobre si encaja con tus objetivos."),
        ),
        takeaway="Antes de guardar, confirma identidad, estructura, cantidades y nutrición; después, verifica la copia dentro de tu biblioteca.",
    ),
    LearningArticle(
        slug="asistente-y-propuestas",
        title="Asistente y propuestas",
        summary="Distingue conversación, propuesta revisable y cambio aplicado.",
        icon="sparkles",
        sections=(
            LearningSection("Conversar no equivale a cambiar", "El Asistente puede ayudarte a consultar información, aclarar una intención y preparar alternativas. Una respuesta en el chat no significa por sí sola que una comida, plan, programa o ficha haya sido modificada. Cuando una acción requiere revisión, el sistema la presenta de forma explícita antes de aplicarla."),
            LearningSection("Qué es una propuesta", "Una propuesta es un resultado revisable que mantiene separados el análisis y el cambio definitivo. Puede incluir una estructura nutricional, cantidades y un resumen de la intención. Su estado te permite reconocer si todavía está pendiente, si fue rechazada o si ya siguió el flujo correspondiente."),
            LearningSection("Cómo hacer una buena revisión", "Comprueba que el Asistente entendió a la persona, el objetivo y el elemento correcto. Revisa alimentos, cantidades, comidas, totales y cualquier advertencia visible. Si el contenido no representa tu intención, no lo apliques: corrige la solicitud, ajusta el contexto o descarta la propuesta."),
            LearningSection("Confirmar y verificar", "Aplicar o confirmar es una decisión separada del chat. Después de hacerlo, abre el elemento resultante y comprueba que el cambio esperado quedó guardado. Si el Asistente te dirige a una pantalla especializada, completa allí el flujo; esa derivación conserva controles que no corresponde reemplazar con una conversación."),
        ),
        takeaway="Distingue siempre conversación, propuesta y cambio aplicado; revisa el resultado final en la pantalla correspondiente.",
    ),
)


CATALOGS = {"nutrition": NUTRITION_FOUNDATIONS, "manuals": SYSTEM_MANUALS}


def catalog_payload() -> dict:
    return {key: [asdict(article) for article in articles] for key, articles in CATALOGS.items()}


def find_article(kind: str, slug: str) -> LearningArticle | None:
    return next((article for article in CATALOGS.get(kind, ()) if article.slug == slug), None)
