from notas.application.services.access.capabilities import get_capabilities
from notas.presentation.composition.viewmodel.components.builder_headers import build_meal_header
from notas.presentation.viewmodels.content.dailyplan.configure_vm import *


def build_meal_configure_vm(meal, user, viewmode):

    caps = get_capabilities(user)

    header = build_meal_header(
        meal=meal,
        user=user,
        viewmode=viewmode
    )

    sections = [

        ConfigureSectionUI(
            title="Visibility",
            fields=[
                ConfigureFieldUI(
                    name="is_public",
                    label="Share this meal in explore",
                    value=meal.is_public,
                    enabled=caps.can_publish(),
                    hint="🔒 Publishing is available for nutritionists"
                )
            ]
        ),

        ConfigureSectionUI(
            title="Permissions",
            fields=[
                ConfigureFieldUI(
                    name="is_forkable",
                    label="Allow forks",
                    value=meal.is_forkable,
                    enabled=True
                ),

                ConfigureFieldUI(
                    name="is_copiable",
                    label="Allow copies",
                    value=meal.is_copiable,
                    enabled=caps.can_copy(),
                    hint="🔒 Copies available on higher plans"
                )
            ]
        )
    ]

    return ConfigureVM(
        header=header,
        sections=sections
    )