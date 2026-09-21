from app.api.schemes import router as schemes_router
from app.api.analytics import router as analytics_router
from app.api.overlap import router as overlap_router
from app.api.recommendations import router as recommendations_router

__all__ = ['schemes_router', 'analytics_router', 'overlap_router', 'recommendations_router']
