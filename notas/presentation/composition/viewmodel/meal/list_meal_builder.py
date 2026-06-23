from notas.presentation.viewmodels.content.meal.list_meal_vm import *
from notas.presentation.config.viewmodel_config import ALLOC_PCT_OUTSIDE_THRESHOLD
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header


def _resolve_title_url(actions):
    for action in actions:
        if action.get("key") in {"detail", "explore_detail", "shared_detail", "draft_detail"}:
            if action.get("method") == "get" and action.get("url"):
                return action["url"]
    return None


def build_meal_list_vm(content_data, page_actions=None, list_mode="list"):
    children = []

    if list_mode in {"reorder", "delete"}:
        for child_data in content_data.child_cards_data:
            children.append({
                "child_id": child_data["child_id"],
                "titulo": {"name": child_data["title"]["name"]},
            })
        return ListVM(
            header=build_page_header(actions=page_actions or []),
            child_cards=children,
            list_mode=list_mode,
        )

    for child_data in content_data.child_cards_data:
        title_url = _resolve_title_url(child_data["actions"])

        child = ChildCardUI(
            child_id=child_data["child_id"],

            titulo=TitleUI(
                name=child_data["title"]["name"],
                label=child_data["title"]["label"],
                icon=child_data["title"]["icon"],
                category=child_data["title"]["category"],
                category_badge=child_data["title"]["category_badge"],
                structural_indicators=StructuralIndicatorsUI(
                    foods_count=child_data["title"]["foods_count"],
                ),
                url=title_url,
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
                pct_outside_protein=(
                    child_data["kpis"]["alloc_protein"] < ALLOC_PCT_OUTSIDE_THRESHOLD
                ),
                pct_outside_carbs=(
                    child_data["kpis"]["alloc_carbs"] < ALLOC_PCT_OUTSIDE_THRESHOLD
                ),
                pct_outside_fat=(
                    child_data["kpis"]["alloc_fat"] < ALLOC_PCT_OUTSIDE_THRESHOLD
                ),
            ),

            table={"items": child_data["table_items"]},

            foods_aggregation=child_data["foods_aggregation"],

            metadata=MetadataUI(
                owner=child_data["metadata"]["owner"],
                author=child_data["metadata"]["author"],
                fork_from=child_data["metadata"]["fork_from"],
            ),

            actions=child_data["actions"],
        )

        children.append(child)

    return ListVM(
        header=build_page_header(actions=page_actions or []),
        child_cards=children,
        list_mode=list_mode,
    )