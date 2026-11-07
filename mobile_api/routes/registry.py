from mobile_api.routes.calendar import router as calendar_router
from mobile_api.routes.calendarization_edits import router as calendarization_edits_router
from mobile_api.routes.comparison_edits import router as comparison_edits_router
from mobile_api.routes.explore import router as explore_router
from mobile_api.routes.list_actions import router as list_actions_router
from mobile_api.routes.notifications import router as notifications_router
from mobile_api.routes.supplements import router as supplements_router

routers = (
    calendar_router,
    calendarization_edits_router,
    list_actions_router,
    notifications_router,
    comparison_edits_router,
    supplements_router,
    explore_router,
)
