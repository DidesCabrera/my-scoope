from notas.presentation.config.viewmode import vm

# HOME ----------------------------------------------
HOME_VIEWMODE = vm("home", "list", "personal")

# PROFILE  -------------------------------------------
PROFILE_VIEWMODE = vm("profile", "list", "personal")
BILLING_VIEWMODE = vm("billing", "list", "personal")


# FOOD  ---------------------------------------------
FOOD_VIEWMODE_PERSONAL_LIST = vm("food", "list", "personal")
FOOD_VIEWMODE_PERSONAL_DETAIL = vm("food", "detail", "personal")
FOOD_VIEWMODE_PERSONAL_EDIT = vm("food", "edit", "personal")

FOOD_VIEWMODE_CREATE = vm("food", "list", "create")
FOOD_VIEWMODE_CONFIGURE = vm("food", "configure", "create")
FOOD_VIEWMODE_IMPORT = vm("food", "list", "import")

FOOD_VIEWMODE_MEAL = vm("food", "meal")

# MF ---------------------------------------------
MEAL_FOOD_VIEWMODE_LIST = vm("meal_food", "list", "personal")
MEAL_FOOD_VIEWMODE_DETAIL = vm("meal_food", "detail", "personal")
MEAL_FOOD_VIEWMODE_PERSONAL_DEEP_EDIT = vm("meal_food", "deep_edit", "personal")
MEAL_FOOD_VIEWMODE_DRAFT_DEEP_EDIT = vm("meal_food", "deep_edit", "draft")

# MEAL ---------------------------------------------
MEAL_VIEWMODE_PERSONAL_LIST = vm("meal", "list", "personal")
MEAL_VIEWMODE_PERSONAL_DETAIL = vm("meal", "detail", "personal")
MEAL_VIEWMODE_PERSONAL_EDIT_FROM_DAILYPLAN = vm("meal", "edit_from_dailyplan", "personal")

MEAL_VIEWMODE_EXPLORE_LIST = vm("meal", "list", "explore")
MEAL_VIEWMODE_EXPLORE_DETAIL = vm("meal", "detail", "explore")

MEAL_VIEWMODE_SHARED_LIST = vm("meal", "list", "shared")
MEAL_VIEWMODE_SHARED_DETAIL = vm("meal", "detail", "shared")

MEAL_VIEWMODE_DRAFT_LIST = vm("meal", "list", "draft")
MEAL_VIEWMODE_DRAFT_DETAIL = vm("meal", "detail", "draft")
MEAL_VIEWMODE_DRAFT_EDIT = vm("meal", "edit", "draft")

MEAL_VIEWMODE_CREATE = vm("meal", "list", "create")
MEAL_VIEWMODE_CONFIGURE = vm("meal", "configure", "personal")

MEAL_VIEWMODE_DAILYPLAN = vm("meal", "dailyplan")




# DAILYPLAN ---------------------------------------------
DAILYPLAN_VIEWMODE_PERSONAL_LIST = vm("dailyplan", "list", "personal")
DAILYPLAN_VIEWMODE_PERSONAL_DETAIL = vm("dailyplan", "detail", "personal")

DAILYPLAN_VIEWMODE_EXPLORE_LIST = vm("dailyplan", "list", "explore")
DAILYPLAN_VIEWMODE_EXPLORE_DETAIL = vm("dailyplan", "detail", "explore")

DAILYPLAN_VIEWMODE_SHARED_LIST = vm("dailyplan", "list", "shared")
DAILYPLAN_VIEWMODE_SHARED_DETAIL = vm("dailyplan", "detail", "shared")

DAILYPLAN_VIEWMODE_DRAFT_LIST = vm("dailyplan", "list", "draft")
DAILYPLAN_VIEWMODE_DRAFT_DETAIL = vm("dailyplan", "detail", "draft")
DAILYPLAN_VIEWMODE_DRAFT_EDIT = vm("dailyplan", "edit", "draft")

DAILYPLAN_VIEWMODE_CREATE = vm("dailyplan", "list", "create")
DAILYPLAN_VIEWMODE_BUILD = vm("dailyplan", "build", "create")
DAILYPLAN_VIEWMODE_CONFIGURE = vm("dailyplan", "configure", "create")


# DPM ---------------------------------------------
DAILYPLAN_MEAL_VIEWMODE_LIST = vm("dailyplan_meal", "list", "personal")
DAILYPLAN_MEAL_VIEWMODE_DETAIL = vm("dailyplan_meal", "detail", "personal")
DAILYPLAN_MEAL_VIEWMODE_EDIT = vm("dailyplan_meal", "edit", "personal")

DAILYPLAN_MEAL_VIEWMODE_DRAFT_DEEP_EDIT = vm("dailyplan_meal", "deep_edit", "draft")


# DPM OTRO (PARA DEJAR PORCENTAJE DE ALLOC FUERA O DENTRO---------------------------------------------
ALLOC_PCT_OUTSIDE_THRESHOLD = 10


ADMIN_HOME_VIEWMODE = vm("admin", "list", "admin")
ADMIN_FOOD_CATALOG_VIEWMODE = vm("admin", "list", "foods")
ADMIN_ANALYTICS_OVERVIEW_VIEWMODE = vm("admin_analytics", "list", "overview")
ADMIN_OPERATIONS_OVERVIEW_VIEWMODE = vm("admin_operations", "list", "overview")


# PROGRAM ---------------------------------------------
PROGRAM_VIEWMODE_PERSONAL_LIST = vm("program", "list", "personal")
PROGRAM_VIEWMODE_PERSONAL_DETAIL = vm("program", "detail", "personal")
PROGRAM_VIEWMODE_CREATE = vm("program", "list", "create")
PROGRAM_VIEWMODE_CONFIGURE = vm("program", "configure", "personal")
PROGRAM_VIEWMODE_SHARE = vm("program", "share", "personal")

# CALENDARIZATION -------------------------------------
CALENDARIZATION_VIEWMODE_DASHBOARD = vm("calendarization", "list", "personal")
CALENDARIZATION_VIEWMODE_DAY_DETAIL = vm("calendarization", "detail", "personal")
CALENDARIZATION_VIEWMODE_HISTORY = vm("calendarization", "list", "history")


# PROPOSAL ---------------------------------------------
PROPOSAL_VIEWMODE_LIST = vm("proposal", "list", "personal")
PROPOSAL_VIEWMODE_DETAIL = vm("proposal", "detail", "personal")


# COMPARATORS ---------------------------------------------
COMPARATOR_VIEWMODE_FOODS = vm("comparator", "list", "foods")
COMPARATOR_VIEWMODE_MEALS = vm("comparator", "list", "meals")
COMPARATOR_VIEWMODE_DAILYPLANS = vm("comparator", "list", "dailyplans")


# AI CHATS ---------------------------------------------
CHAT_VIEWMODE_LIST = vm("chat", "list", "personal")
CHAT_VIEWMODE_DETAIL = vm("chat", "detail", "personal")


# INBOX / SHARING ---------------------------------------------
INBOX_VIEWMODE_LIST = vm("inbox", "list", "personal")
INBOX_VIEWMODE_DETAIL = vm("inbox", "detail", "personal")
