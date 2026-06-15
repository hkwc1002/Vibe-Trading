"""API router exports for the Low Absorb workspace."""

from __future__ import annotations

from .backtest import router as backtest_router
from .chain import router as chain_router
from .data_sources import router as data_sources_router
from .reports import router as reports_router
from .sentiment import router as sentiment_router
from .settings import router as settings_router
from .workbench import router as workbench_router

__all__ = [
    "backtest_router",
    "chain_router",
    "data_sources_router",
    "reports_router",
    "sentiment_router",
    "settings_router",
    "workbench_router",
    "register_low_absorb_routes",
]


def register_low_absorb_routes(app, *, dependencies=None) -> None:

    app.include_router(workbench_router, dependencies=dependencies or [])
    app.include_router(sentiment_router, dependencies=dependencies or [])
    app.include_router(chain_router, dependencies=dependencies or [])
    app.include_router(backtest_router, dependencies=dependencies or [])
    app.include_router(reports_router, dependencies=dependencies or [])
    app.include_router(settings_router, dependencies=dependencies or [])
    app.include_router(data_sources_router, dependencies=dependencies or [])
