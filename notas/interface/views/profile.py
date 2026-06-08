from dataclasses import dataclass
from typing import List, Optional

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from notas.presentation.config.viewmodel_config import PROFILE_VIEWMODE
from notas.presentation.viewmodels.base_vm import BaseVM
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.application.services.nutrition.weight import get_current_weight_log


@dataclass
class ProfileStatVM:
    label: str
    value: str
    icon: str


@dataclass
class ProfileContentVM:
    title: str
    subtitle: str
    stats: List[ProfileStatVM]
    weight_current: Optional[float]
    weight_updated_at: Optional[str]


@login_required
def profile_detail(request):
    user = request.user
    profile = user.profile

    last_weight_log = get_current_weight_log(user)
    current_weight = last_weight_log.weight_kg if last_weight_log else None

    content = ProfileContentVM(
        title=f"{user.username}",
        subtitle=(
            "Gestiona tu información de cuenta y el peso corporal usado "
            "como referencia para el cálculo de proteína por kilo."
        ),
        stats=[
            ProfileStatVM(
                label="Rol",
                value=profile.get_role_display(),
                icon="badge-check",
            ),
            ProfileStatVM(
                label="Plan",
                value=profile.plan.name if profile.plan else "Sin plan",
                icon="credit-card",
            ),
            ProfileStatVM(
                label="Peso actual",
                value=f"{current_weight:.1f} kg" if current_weight else "Sin registro",
                icon="scale",
            ),
        ],
        weight_current=current_weight,
        weight_updated_at=(
            last_weight_log.date.strftime("%Y-%m-%d")
            if last_weight_log else None
        ),
    )

    ui = build_ui_vm(PROFILE_VIEWMODE)

    vm = BaseVM(
        ui=ui,
        content=content,
    )

    context = vm.as_context()
    context["profile"] = profile

    return render(
        request,
        "notas/profile/detail.html",
        context,
    )