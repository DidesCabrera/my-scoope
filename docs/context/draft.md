Necesito realizar los siguientes ajustes:

List:
-Quitar proposal-list-card__eyebrow-row
-En dektop poner el proposal-status-badge entre proposal-list-card__main y proposal-list-card__metadata (cono esta en mobile)
-Poner el icono de proposal AI arriba a la derecha. (Basarse en como se dispone el icono de la entidad dentro de card-title-comp)
-Estilizar la accion de Ver propuesta como se ve la ccion de ir a detail desde una child card.


En detail:
-Quitar proposal-list-card__eyebrow-row
-Poner el icono de proposal AI arriba a la derecha. (Basarse en como se dispone el icono de la entidad dentro de card-title-comp)
-al igual que en la vista, orientar proposal-review-summary al requerimiento y dejarlo dentro de un bloque.
- Borraría el contexto como esta (proposal-review-context), y Pondria en una linea primero el nombre de la entidad (junto a su icono) y debajo pondria la metadata.
-Me gustaría que lo que apareciera como entidad fuera solo la child card del elemento "padre y que al igual que otras child cards tuviera la accion de "entrar" al detalle. El cual, para nuevas comidas o dailyplan; debería verse igual (el caso de proponer diferencias o cambios sobre existentes lo trabajaremos posteriormente).


Favor Revisar el ZIP actualizado y entregarme un patch para aplicar los cambios necesario para conseguir el resultado deseado.
