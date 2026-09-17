from ninja import Router

from mobile_api.routes.billing import router as apple_billing_router
from mobile_api.routes.google_play_billing import router as google_play_billing_router

router = Router()
router.add_router("", apple_billing_router)
router.add_router("", google_play_billing_router)
