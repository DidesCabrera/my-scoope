from ninja import Router

from mobile_api.routes.home import router as home_router
from mobile_api.routes.identity import router as identity_router

router = Router()
router.add_router("", identity_router)
router.add_router("", home_router)
