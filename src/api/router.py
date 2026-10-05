from fastapi import APIRouter

from src.api.routes.health import router as health_router
from src.api.routes.novel import router as novel_router
from src.api.routes.speech import router as speech_router
from src.api.routes.voices import router as voices_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(voices_router)
api_router.include_router(speech_router)
api_router.include_router(novel_router)
