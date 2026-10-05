from typing import Optional
from src.engines.base import BaseTTSEngine
from src.engines.vieneu import VieNeuEngine
from src.services.novel_service import NovelPipelineService

# Singleton instances
_engine_instance: Optional[BaseTTSEngine] = None
_novel_service_instance: Optional[NovelPipelineService] = None


def get_engine() -> BaseTTSEngine:
    """Dependency cung cấp Singleton TTS Engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = VieNeuEngine()
    return _engine_instance


def get_novel_service() -> NovelPipelineService:
    """Dependency cung cấp Singleton Novel Pipeline Service."""
    global _novel_service_instance
    if _novel_service_instance is None:
        engine = get_engine()
        _novel_service_instance = NovelPipelineService(engine=engine)
    return _novel_service_instance
