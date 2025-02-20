from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from ....services.history import HistoryService
from ....services.asset import AssetService
from ....core.utils import TEMP_USER_ID

router = APIRouter()


@router.post("/snapshot")
async def create_snapshot(user_id: str = TEMP_USER_ID):
    """创建当前投资组合快照

    在开发/测试阶段，可以：
    1. 不传入 user_id 参数，将使用默认的 TEMP_USER_ID
    2. 显式传入 TEMP_USER_ID: 123e4567-e89b-12d3-a456-426614174000

    未来在生产环境中，user_id 将从认证令牌中获取
    """
    # 获取用户所有资产
    # assets = await AssetService.get_assets(user_id)

    # 记录快照
    success = await HistoryService.record_portfolio_snapshot(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to create snapshot")
    return {"message": "Snapshot created successfully"}


@router.get("/portfolio")
async def get_portfolio_history(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user_id: str = TEMP_USER_ID,
):
    """获取投资组合历史记录"""
    return await HistoryService.get_portfolio_history(user_id, start_date, end_date)


@router.get("/asset/{symbol}")
async def get_asset_history(
    symbol: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user_id: str = TEMP_USER_ID,
):
    """获取单个资产的历史记录"""
    return await HistoryService.get_asset_history(user_id, symbol, start_date, end_date)


@router.get("/stats")
async def get_portfolio_stats(user_id: str = TEMP_USER_ID):
    """获取投资组合统计数据，包括每个资产的24小时变化"""
    return await HistoryService.calculate_portfolio_stats(user_id)
