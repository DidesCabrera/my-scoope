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
            LearningSection("No existe una única dieta perfecta", "Una alimentación saludable se adapta a la edad, actividad, cultura, disponibilidad de alimentos y situación de cada persona."),
            LearningSection("Cuatro ideas guía", "Adecuación significa cubrir necesidades; equilibrio, relacionar energía y nutrientes; moderación, evitar excesos; y diversidad, incluir distintos alimentos y grupos."),
        ),
        takeaway="Evalúa el patrón completo y su sostenibilidad, no un alimento aislado.",
        source_label="OMS · Alimentación saludable",
        source_url="https://www.who.int/es/news-room/fact-sheets/detail/healthy-diet",
    ),
    LearningArticle(
        slug="energia-y-calorias",
        title="Energía, calorías y balance",
        summary="Cómo se relacionan la energía ingerida, el gasto y los objetivos corporales.",
        icon="flame",
        sections=(
            LearningSection("Las calorías expresan energía", "Los alimentos aportan energía y el cuerpo la utiliza para funciones básicas, actividad y entrenamiento."),
            LearningSection("Las estimaciones son un punto de partida", "Edad, sexo nutricional, altura, peso y actividad permiten estimar necesidades. La respuesta real puede variar y se ajusta observando tendencias."),
        ),
        takeaway="Usa los cálculos como referencia revisable, no como una verdad exacta.",
        source_label="EFSA · Valores dietéticos de referencia",
        source_url="https://www.efsa.europa.eu/en/topics/topic/dietary-reference-values",
    ),
    LearningArticle(
        slug="macronutrientes",
        title="Proteínas, carbohidratos y grasas",
        summary="El papel de los tres macronutrientes que My Scoope muestra en comidas y planes.",
        icon="chart-no-axes-column-increasing",
        sections=(
            LearningSection("Funciones diferentes", "Las proteínas aportan aminoácidos; los carbohidratos son una fuente importante de energía; y las grasas cumplen funciones celulares y aportan ácidos grasos esenciales."),
            LearningSection("Importan cantidad y calidad", "Una distribución puede variar según el contexto. También importa elegir fuentes variadas y priorizar carbohidratos ricos en fibra y grasas insaturadas."),
        ),
        takeaway="Los macros describen la composición del plan; no resumen por sí solos toda su calidad.",
        source_label="OMS · Alimentación saludable",
        source_url="https://www.who.int/en/news-room/fact-sheets/detail/healthy-diet",
    ),
    LearningArticle(
        slug="proteina-por-kilo",
        title="Proteína por kilogramo (PPK)",
        summary="Por qué My Scoope relaciona la proteína con el peso de la ficha personal.",
        icon="badge-info",
        sections=(
            LearningSection("Una medida relativa", "PPK divide los gramos diarios de proteína por el peso de referencia en kilogramos. Permite interpretar la proteína en relación con la persona."),
            LearningSection("El peso de referencia importa", "Si el peso de la ficha cambia, el PPK visible puede cambiar aunque la comida conserve los mismos gramos de proteína."),
        ),
        takeaway="Mantén actualizado el peso y revisa gramos totales junto con PPK.",
        source_label="EFSA · Valores dietéticos de referencia",
        source_url="https://www.efsa.europa.eu/en/topics/topic/dietary-reference-values",
    ),
    LearningArticle(
        slug="calidad-variedad-y-fibra",
        title="Calidad, variedad y fibra",
        summary="Por qué dos planes con macros parecidos pueden tener distinta calidad alimentaria.",
        icon="salad",
        sections=(
            LearningSection("Mirar más allá de los números", "Frutas, verduras, legumbres, cereales integrales, frutos secos y fuentes variadas de proteína ayudan a cubrir fibra y micronutrientes."),
            LearningSection("La variedad reduce puntos ciegos", "Rotar alimentos dentro de un patrón coherente facilita obtener distintos nutrientes y evita depender de una selección demasiado estrecha."),
        ),
        takeaway="Combina objetivos cuantitativos con variedad y alimentos de buena calidad.",
        source_label="OMS · Alimentación saludable",
        source_url="https://www.who.int/es/news-room/fact-sheets/detail/healthy-diet",
    ),
    LearningArticle(
        slug="seguimiento-y-ajustes",
        title="Seguimiento y ajustes",
        summary="Cómo interpretar cambios de peso y adaptar un plan sin reaccionar a un solo dato.",
        icon="line-chart",
        sections=(
            LearningSection("Una medición no define una tendencia", "El peso puede variar por hidratación, contenido digestivo y otros factores. Conviene observar varias mediciones comparables."),
            LearningSection("Ajustar con contexto", "Adherencia, energía, rendimiento, hambre y evolución del objetivo ayudan a decidir si un plan necesita cambios."),
        ),
        takeaway="Busca tendencias y realiza cambios graduales con suficiente información.",
    ),
)


SYSTEM_MANUALS = (
    LearningArticle(
        slug="fichas-personales",
        title="Fichas personales",
        summary="Mantén actualizados los datos que alimentan cálculos, objetivos y planes.",
        icon="files",
        sections=(
            LearningSection("Qué reúnen", "La ficha corporal, objetivo y actividad, preferencias alimentarias y métricas corporales viven en un solo lugar."),
            LearningSection("Cuándo editarlas", "Actualiza la información cuando cambien tus datos o contexto. Los cálculos futuros usarán la versión persistida más reciente."),
        ),
        takeaway="Entra desde el sidebar y usa “Editar información” en la ficha correspondiente.",
    ),
    LearningArticle(
        slug="bibliotecas",
        title="Bibliotecas y jerarquía",
        summary="Entiende cómo se relacionan alimentos, comidas, planes diarios y programas.",
        icon="library-big",
        sections=(
            LearningSection("De menor a mayor", "Los alimentos forman comidas; las comidas forman planes diarios; y los planes diarios se organizan en programas semanales."),
            LearningSection("Elementos reutilizables", "Las bibliotecas guardan tus elementos para consultarlos, duplicarlos, compartirlos o incorporarlos en estructuras mayores."),
        ),
        takeaway="Edita cada nivel desde su biblioteca y revisa el impacto en el contexto donde se utiliza.",
    ),
    LearningArticle(
        slug="programa-activo",
        title="Inicio y programa activo",
        summary="Consulta qué corresponde hoy y recorre la planificación calendarizada.",
        icon="calendar-clock",
        sections=(
            LearningSection("Inicio", "La pantalla de inicio prioriza el plan vigente y las acciones del día."),
            LearningSection("Programa activo", "La vista del programa permite recorrer semanas y días, registrar ejecución y consultar la estructura planificada."),
        ),
        takeaway="Usa Inicio para ejecutar el día y Programa activo para comprender el calendario completo.",
    ),
    LearningArticle(
        slug="comparaciones",
        title="Comparaciones",
        summary="Compara alimentos, comidas o planes usando el mismo contexto nutricional.",
        icon="scale",
        sections=(
            LearningSection("Comparar elementos equivalentes", "Selecciona dos elementos del mismo tipo para revisar sus diferencias nutricionales y estructurales."),
            LearningSection("Interpretar el resultado", "Una diferencia numérica no declara automáticamente un ganador; el objetivo y el contexto determinan qué opción resulta más adecuada."),
        ),
        takeaway="Usa la comparación como apoyo para decidir, no como una clasificación universal.",
    ),
    LearningArticle(
        slug="compartidos",
        title="Compartidos",
        summary="Recibe elementos de otros usuarios y decide si incorporarlos a tu biblioteca.",
        icon="user-plus",
        sections=(
            LearningSection("Revisar antes de guardar", "Los elementos recibidos se presentan con su información disponible para que puedas evaluarlos."),
            LearningSection("Tu biblioteca conserva el control", "Guardar un elemento crea una copia utilizable en tu espacio; no modifica la biblioteca de quien lo compartió."),
        ),
        takeaway="Revisa identidad, estructura y nutrición antes de guardar un elemento compartido.",
    ),
    LearningArticle(
        slug="asistente-y-propuestas",
        title="Asistente y propuestas",
        summary="Distingue conversación, propuesta revisable y cambio aplicado.",
        icon="sparkles",
        sections=(
            LearningSection("Conversar no siempre modifica", "El Asistente puede consultar contexto y preparar una propuesta. Las acciones relevantes se presentan para revisión."),
            LearningSection("Revisar antes de aplicar", "Una propuesta permite inspeccionar la estructura y reconocer sus efectos antes de guardarla o aplicarla."),
        ),
        takeaway="Confirma los datos, revisa la propuesta y aplica solo cuando represente tu intención.",
    ),
)


CATALOGS = {"nutrition": NUTRITION_FOUNDATIONS, "manuals": SYSTEM_MANUALS}


def catalog_payload() -> dict:
    return {key: [asdict(article) for article in articles] for key, articles in CATALOGS.items()}


def find_article(kind: str, slug: str) -> LearningArticle | None:
    return next((article for article in CATALOGS.get(kind, ()) if article.slug == slug), None)
