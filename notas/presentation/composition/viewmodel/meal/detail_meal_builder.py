from notas.presentation.viewmodels.content.meal.detail_meal_vm import *


def build_meal_detail_vm(content_data):
    main = MainCardUI(
        main_id=content_data.main_card_data["main_id"],
        titulo=TitleUI(
            name=content_data.main_card_data["title"]["name"],
            label=content_data.main_card_data["title"]["label"],
            icon=content_data.main_card_data["title"]["icon"],
            category=content_data.main_card_data["title"]["category"],
            category_badge=content_data.main_card_data["title"]["category_badge"],
            structural_indicators=StructuralIndicatorsUI(
                foods_count=content_data.main_card_data["title"]["foods_count"],
            ),
        ),
        kpis=KPIUI(
            ppk=content_data.main_card_data["kpis"]["ppk"],
            tot_kcal=content_data.main_card_data["kpis"]["tot_kcal"],
            g_protein=content_data.main_card_data["kpis"]["g_protein"],
            g_carbs=content_data.main_card_data["kpis"]["g_carbs"],
            g_fat=content_data.main_card_data["kpis"]["g_fat"],
            kcal_protein=content_data.main_card_data["kpis"]["kcal_protein"],
            kcal_carbs=content_data.main_card_data["kpis"]["kcal_carbs"],
            kcal_fat=content_data.main_card_data["kpis"]["kcal_fat"],
            alloc_protein=content_data.main_card_data["kpis"]["alloc_protein"],
            alloc_carbs=content_data.main_card_data["kpis"]["alloc_carbs"],
            alloc_fat=content_data.main_card_data["kpis"]["alloc_fat"],
        ),
        table={"items": content_data.table_items},
        foods_aggregation=content_data.main_card_data["foods_aggregation"],
        metadata=MetadataUI(
            owner=content_data.main_card_data["metadata"]["owner"],
            author=content_data.main_card_data["metadata"]["author"],
            fork_from=content_data.main_card_data["metadata"]["fork_from"],
        ),
        show_kpis=content_data.main_card_data["show_kpis"],
        show_table=content_data.main_card_data["show_table"],
    )

    child_cards = []

    for child_data in content_data.child_cards_data:
        child = ChildCardUI(
            child_id=child_data["child_id"],
            related_data=MfRelatedDataUI(
                rel_id=child_data["related_data"]["rel_id"],
                quantity=child_data["related_data"]["quantity"],
                alloc_protein=child_data["related_data"]["alloc_protein"],
                alloc_carbs=child_data["related_data"]["alloc_carbs"],
                alloc_fat=child_data["related_data"]["alloc_fat"],
            ),
            titulo=TitleUI(
                name=child_data["title"]["name"],
                label=child_data["title"]["label"],
                icon=child_data["title"]["icon"],
                category=child_data["title"]["category"],
                category_badge=child_data["title"]["category_badge"],
            ),
            kpis=KPIUI(
                ppk=child_data["kpis"]["ppk"],
                tot_kcal=child_data["kpis"]["tot_kcal"],
                g_protein=child_data["kpis"]["g_protein"],
                g_carbs=child_data["kpis"]["g_carbs"],
                g_fat=child_data["kpis"]["g_fat"],
                kcal_protein=child_data["kpis"]["kcal_protein"],
                kcal_carbs=child_data["kpis"]["kcal_carbs"],
                kcal_fat=child_data["kpis"]["kcal_fat"],
                alloc_protein=child_data["kpis"]["alloc_protein"],
                alloc_carbs=child_data["kpis"]["alloc_carbs"],
                alloc_fat=child_data["kpis"]["alloc_fat"],
            ),
            actions=child_data["actions"],
        )
        child_cards.append(child)

    return MealDetailVM(
        header=content_data.header,
        main_card=main,
        child_cards=child_cards,
    )