from fastapi import APIRouter
from .endpoints import portfolio, assets, history

api_router = APIRouter()

# 在这里导入和注册其他路由
# from .endpoints import portfolio, user, history
# api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
