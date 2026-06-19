from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class NavItemSpec:
    key: str
    label: str
    icon: str
    url_name: str
    nav_root: str
    scope: Optional[str] = None
    page_icon: Optional[str] = None
    show_in_sidebar: bool = True


@dataclass(frozen=True)
class NavGroupSpec:
    key: str
    label: str
    icon: str
    items: tuple[NavItemSpec, ...] = field(default_factory=tuple)
    url_name: Optional[str] = None
    nav_root: Optional[str] = None
    scope: Optional[str] = None
    page_icon: Optional[str] = None
    show_in_sidebar: bool = True

    action_url_name: Optional[str] = None
    action_icon: Optional[str] = None
    action_label: Optional[str] = None

    @property
    def is_link(self) -> bool:
        return bool(self.url_name) and not self.items


@dataclass(frozen=True)
class NavSectionSpec:
    key: str
    label: str
    groups: tuple[NavGroupSpec, ...] = field(default_factory=tuple)


APP_NAVIGATION = (
    NavSectionSpec(
        key="workspace",
        label="Mis Librerías",
        groups=(
            NavGroupSpec(
                key="program",
                label="Mis Programas Semanales",
                icon="calendar",
                url_name="program_list",
                nav_root="program",
                scope="personal",
                page_icon="bookmark",
                action_url_name="program_create",
                action_icon="plus",
                action_label="Nuevo programa semanal",
            ),
            NavGroupSpec(
                key="dailyplan",
                label="Mis Planes Diarios",
                icon="clipboard-list",
                url_name="dailyplan_list",
                nav_root="dailyplan",
                scope="personal",
                page_icon="bookmark",
                action_url_name="dailyplan_create",
                action_icon="plus",
                action_label="Nuevo plan diario",
            ),
            NavGroupSpec(
                key="meal",
                label="Mis Comidas",
                icon="utensils",
                url_name="meal_list",
                nav_root="meal",
                scope="personal",
                page_icon="bookmark",
                action_url_name="meal_create",
                action_icon="plus",
                action_label="Nueva comida",
            ),
            NavGroupSpec(
                key="food",
                label="Mis Alimentos",
                icon="carrot",
                url_name="food_list",
                nav_root="food",
                scope="personal",
                page_icon="bookmark",
                action_url_name="food_create",
                action_icon="plus",
                action_label="Nuevo alimento",
            ),
        ),
    ),

    NavSectionSpec(
        key="account",
        label="Tools",
        groups=(
            NavGroupSpec(
                key="home",
                label="Home",
                icon="house",
                page_icon="house",
                url_name="home_view",
                nav_root="home",
                scope="personal",
                show_in_sidebar=False,
            ),
            NavGroupSpec(
                key="profile",
                label="Mi Perfil",
                icon="circle-user-round",
                url_name="profile_detail",
                nav_root="profile",
                scope="personal",
                page_icon="circle-user-round",
                show_in_sidebar=False,
            ),
            NavGroupSpec(
                key="inbox",
                label="Inbox",
                icon="inbox",
                page_icon="inbox",
                url_name="inbox_list",
                nav_root="inbox",
                scope="personal",
            ),
            NavGroupSpec(
                key="proposal",
                label="Propuestas AI",
                icon="sparkles",
                page_icon="sparkles",
                url_name="proposal_list",
                nav_root="proposal",
                scope="personal",
            ),
            NavGroupSpec(
                key="explore",
                label="Explorar",
                icon="search",
                items=(
                    NavItemSpec(
                        key="dailyplan_explore",
                        label="Explorar Planes",
                        icon="clipboard-list",
                        page_icon="search",
                        url_name="dailyplan_explore_list",
                        nav_root="dailyplan",
                        scope="explore",
                    ),
                    NavItemSpec(
                        key="meal_explore",
                        label="Explorar Comidas",
                        icon="utensils",
                        page_icon="search",
                        url_name="meal_explore_list",
                        nav_root="meal",
                        scope="explore",
                    ),
                ),
            ),
            NavGroupSpec(
                key="create",
                label="Crear",
                icon="circle-fading-plus",
                show_in_sidebar=False,
                items=(
                    NavItemSpec(
                        key="dailyplan_create",
                        label="Nuevo Plan",
                        icon="clipboard-list",
                        page_icon="circle-fading-plus",
                        url_name="dailyplan_create",
                        nav_root="dailyplan",
                        scope="create",
                    ),
                    NavItemSpec(
                        key="program_create",
                        label="Nuevo Programa",
                        icon="calendar",
                        page_icon="circle-fading-plus",
                        url_name="program_create",
                        nav_root="program",
                        scope="create",
                    ),
                    NavItemSpec(
                        key="meal_create",
                        label="Nueva Comida",
                        icon="utensils",
                        page_icon="circle-fading-plus",
                        url_name="meal_create",
                        nav_root="meal",
                        scope="create",
                    ),
                    NavItemSpec(
                        key="food_create",
                        label="Nuevo Alimento",
                        icon="carrot",
                        page_icon="circle-fading-plus",
                        url_name="food_create",
                        nav_root="food",
                        scope="create",
                    ),
                    NavItemSpec(
                        key="food_import",
                        label="Importar Alimentos",
                        icon="file-down",
                        page_icon="file-down",
                        url_name="import_foods",
                        nav_root="food",
                        scope="import",
                    ),
                ),
            ),
        ),
    ),

    NavSectionSpec(
        key="admin",
        label="Admin Workspace",
        groups=(
            NavGroupSpec(
                key="admin",
                label="Admin",
                icon="shield",
                show_in_sidebar=True,
                items=(
                    NavItemSpec(
                        key="admin_home",
                        label="Admin Home",
                        icon="shield",
                        page_icon="shield",
                        url_name="admin_home",
                        nav_root="admin",
                        scope="admin",
                        show_in_sidebar=True,
                    ),
                    NavItemSpec(
                        key="admin_food_catalog",
                        label="Foods Catalog",
                        icon="database",
                        page_icon="database",
                        url_name="admin_food_catalog",
                        nav_root="admin",
                        scope="foods",
                        show_in_sidebar=True,
                    ),
                ),
            ),
        ),
    ),
)
