Necesito que me ayudes a realizar ajustes en My Scoope. Necesito lo siguiente:


Corregir los iconos y colores de secciones. (Navegacion)
Breadcrum clickeables

Sombra search list. y ajustar ancho en desktop

Btn para subir (scroll to top)

que el header global aparezca cuando se oculta el titulo de pagina, no structural indicator

separar botones de acciones en child cards

Separar dash KPI y secciones de paneles en child cards

que tras agregar meal a dailyplan cargue con panel editar por defecto.

Quitar nombre de autor en card meal o dpm?


Que tras eliminar un elemento, vuelva a la pestaña en que esta, y si se elimina un elemento desde detail, que vuelva a las lista a la que pertenecia el elemento eliminado.


resolver incosistencias en detail ede propuestas.
-Sacar hora
-actualizar seccion alimentos

Normalizar barras alloc como barra de kcal


Quitar de home las secciones dailyplans, meals y foods



===================================================================

Revisa la ultima version del codigo dentro del ZIP y genera un patch para modificar el codigo para conseguir el resultado deseado.

Revisa la ultima version del codigo dentro del ZIP y genera un patch que modifique el codigo para conseguir el resultado que se desea.

Revisa la ultima version del codigo dentro del ZIP y genera un patch que modifique el codigo para conseguir el resultado que se desea.

7b5b39






PROMPT COMPARACIONES


Revisa la ultima version del codigo dentro del ZIP y genera un patch que modifique el codigo para conseguir el resultado que se desea.


---


NO APLICADO

Cambios por hacer:

En Home Mobile, en home-stats-card modificar home-stat-top de la siguiente manera: Poner el icono en uen una sola fila arriba, y abajo el home-stat-label. Y tambien que las palabras "programas" y "semanales, y "Planes" y "Diarios" queden en filas separadas.

Revisa la ultima version del codigo dentro del ZIP y genera un patch que modifique el codigo para conseguir el resultado que se desea.




APLICANDO

La implementacion ha sido un exito. Aspectos por mejorar:
1. la lista de opciones no se ve bien en mobile. aparece en miniatura. Adaptarla para un buen funcionamiento en mobile.
2. Mejorar la estetica del boton comparar Similar a la otros btnes del sistema (no usar colores de entidad aqui ni en botones de tabs).
3. poner "comparator-empty card-detail-block" debajo de comparator-tabs.
4. Que el color del fondo del Icono de list-page-header__icon--comparator este alineado con lo que esta comparando (foods, meals, o plans)
5. para los tamaños de letra en comparator-form usar un tamaño minimo de 14px en mobile.
6. Agregar a la comparación entre comidas y plan el PPK. y ponerlo en segunda posición.
7. Para las comparaciones que las barras usen los mismos colores que se usan en los graficos de programs.
8. En comparator-bar-row__meta poner al lado izquierdo del nombre del elemento comparado, el icono de la entidad respectiva.
9. Poner la seccion de comparadores en la segunda posicion en la seccion de tools (debajo de Inbox)
10. En cada vista de list de (foods, meals, y plans) poner dentro del menu de acciones en el header global la opcion de comparar. la cual dirija a la seccion de comparador respectiva.

No hacer cambios adicionales en el CSS

Revisa la ultima version del codigo dentro del ZIP y genera un patch que modifique el codigo para conseguir el resultado que se desea.