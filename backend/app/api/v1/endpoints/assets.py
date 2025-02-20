from typing import List
from fastapi import APIRouter, HTTPException, Depends
from ....schemas.asset import AssetCreate, AssetUpdate, AssetResponse, AssetInDB
from ....services.asset import AssetService
from ....core.utils import TEMP_USER_ID
import logging

# 设置日志记录器
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=AssetResponse)
async def create_asset(
    asset: AssetCreate,
    user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
):
    """创建新资产"""
    try:
        return await AssetService.create_asset(user_id, asset)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[AssetResponse])
async def get_assets(
    user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
):
    """获取用户的所有资产"""
    return await AssetService.get_assets(user_id)


@router.get("/symbol/{symbol}", response_model=AssetResponse)
async def get_asset_by_symbol(
    symbol: str,
    user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
):
    """通过 symbol 获取资产"""
    asset = await AssetService.get_asset_by_symbol(user_id, symbol)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
):
    """获取单个资产详情"""
    asset = await AssetService.get_asset(user_id, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.put("/symbol/{symbol}", response_model=AssetResponse)
async def update_asset_by_symbol(
    symbol: str,
    asset_update: AssetUpdate,
    user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
):
    """通过 symbol 更新资产"""
    asset = await AssetService.update_asset_by_symbol(user_id, symbol, asset_update)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.put("/update")
async def update_asset(asset_update: AssetUpdate, user_id: str = TEMP_USER_ID):
    """更新资产数量"""
    try:
        logger.info(f"Received update request - asset_update: {asset_update.model_dump()}")  # 打印完整的请求数据
        logger.info(f"Request body tokens_holding: {asset_update.tokens_holding}")  # 打印 tokens_holding 值

        updated_asset = await AssetService.update_asset_by_symbol_and_storage(
            user_id=user_id,
            symbol=asset_update.symbol,
            storage=asset_update.storage,
            asset_update=asset_update,  # 直接传递 asset_update 对象
        )

        if not updated_asset:
            logger.error(f"Asset not found: {asset_update}")
            raise HTTPException(status_code=404, detail="Asset not found")

        logger.info(f"Asset updated successfully: {updated_asset.model_dump()}")  # 打印更新后的数据
        return updated_asset
    except Exception as e:
        logger.error(f"Error updating asset: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
):
    """删除资产"""
    success = await AssetService.delete_asset(user_id, asset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted successfully"}


@router.post("/update-prices", response_model=List[AssetResponse])
async def update_prices(
    user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
):
    """更新所有资产的价格"""
    return await AssetService.update_all_prices(user_id)


@router.put("/symbol/{symbol}/storage/{storage}", response_model=AssetResponse)
async def update_asset_by_location(
    symbol: str,
    storage: str,
    asset_update: AssetUpdate,
    user_id: str = TEMP_USER_ID,
):
    """更新特定交易所的资产数量"""
    asset = await AssetService.update_asset_by_symbol_and_storage(user_id, symbol, storage, asset_update)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
