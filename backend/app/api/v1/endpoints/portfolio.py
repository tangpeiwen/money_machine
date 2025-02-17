from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Union

from ....schemas.portfolio import AssetCreate, AssetUpdate, PortfolioResponse
from ....services.portfolio import PortfolioService
from ....core.utils import TEMP_USER_ID

# from ....core.security import get_current_user

router = APIRouter()


@router.get("/", response_model=PortfolioResponse)
async def get_portfolio(
    user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
):
    """获取用户的投资组合"""
    portfolio = await PortfolioService.get_portfolio(user_id)
    if not portfolio:
        portfolio = await PortfolioService.create_portfolio(user_id)
    return portfolio


@router.post("/asset", response_model=PortfolioResponse)
async def add_asset(
    asset: AssetCreate,
    user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
):
    """添加新资产到投资组合"""
    return await PortfolioService.add_asset(user_id, asset)


@router.put("/portfolio/asset/{coin}", response_model=PortfolioResponse)
async def update_asset(
    coin: str,
    asset_update: AssetUpdate,
    user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
):
    """更新资产信息"""
    return await PortfolioService.update_asset(user_id, coin, asset_update)


@router.get("/metrics")
async def get_portfolio_metrics() -> Dict[str, Union[float, str]]:
    try:
        portfolio_service = PortfolioService()
        metrics = await portfolio_service.calculate_metrics()
        return {
            "risk_score": metrics.risk_score,
            "volatility": metrics.volatility,
            "sharpe_ratio": metrics.sharpe_ratio,
            "beta": metrics.beta,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
