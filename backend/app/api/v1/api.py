from fastapi import APIRouter
from .endpoints import portfolio, assets, history, exchange, cryptocurrencies, screenshot

api_router = APIRouter()

api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(exchange.router, prefix="/exchange", tags=["exchange"])
api_router.include_router(cryptocurrencies.router, prefix="/cryptocurrencies", tags=["cryptocurrencies"])
api_router.include_router(screenshot.router, prefix="/screenshot", tags=["screenshot"])
