from typing import List
from fastapi import APIRouter, HTTPException, Depends
from ....schemas.asset import AssetCreate, AssetUpdate, AssetResponse
from ....services.asset import AssetService
from ....core.utils import TEMP_USER_ID

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


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: str,
    asset_update: AssetUpdate,
    user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
):
    """更新资产信息"""
    asset = await AssetService.update_asset(user_id, asset_id, asset_update)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


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
