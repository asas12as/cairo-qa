from fastapi import APIRouter

from api.chat import router as chat_router
from api.browse import router as browse_router
from api.preferences import router as prefs_router
from api.stats import router as stats_router
from api.profiles import router as profiles_router
from api.friends import router as friends_router
from api.messaging import router as messaging_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(browse_router)
router.include_router(prefs_router)
router.include_router(stats_router)
router.include_router(profiles_router)
router.include_router(friends_router)
router.include_router(messaging_router)
