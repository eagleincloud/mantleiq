"""
API routers for MantleIQ application.
"""

from .basins import router as basins_router
from .analysis import router as analysis_router
from .zones import router as zones_router
from .export import router as export_router
from .results import router as results_router

__all__ = ["basins_router", "analysis_router", "zones_router", "export_router", "results_router"]
