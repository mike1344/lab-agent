from fastapi import APIRouter
from app.api.ai import router as ai_router
from app.api.announcement import router as announcement_router
from app.api.auth import router as auth_router
from app.api.blackout import router as blackout_router
from app.api.equipment import router as equipment_router
from app.api.lab import router as lab_router
from app.api.notification import router as notification_router
from app.api.repair import router as repair_router
from app.api.reservation import router as reservation_router
from app.api.stats import router as stats_router
from app.api.upload import router as upload_router
from app.api.user import router as user_router

api = APIRouter(prefix="/api")

api.include_router(auth_router)
api.include_router(user_router)
api.include_router(upload_router)
api.include_router(lab_router)
api.include_router(equipment_router)
api.include_router(reservation_router)
api.include_router(announcement_router)
api.include_router(repair_router)
api.include_router(stats_router)
api.include_router(notification_router)
api.include_router(blackout_router)
api.include_router(ai_router)
