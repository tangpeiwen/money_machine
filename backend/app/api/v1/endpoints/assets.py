from typing import List, Dict
from fastapi import APIRouter, HTTPException, Depends, Query
from ....schemas.asset import AssetCreate, AssetUpdate, AssetResponse, AssetInDB
from ....services.asset import AssetService
from ....core.utils import TEMP_USER_ID, get_crypto_logo
import logging
from ....core.database import db
from ....services.price import PriceService
from ....services.cryptocurrency import CryptocurrencyService
from ....services.dex import DexService

# 设置日志记录器
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=AssetResponse)
async def create_asset(
    asset: AssetCreate,
    # user_id: str = TEMP_USER_ID,
    user_id: str = Query(..., description="User ID from authentication"),
):
    """创建新资产"""
    try:
        logger.info(f"Received create asset request: {asset}")

        # 验证输入数据
        if not asset.symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")
        if not asset.storage:
            raise HTTPException(status_code=400, detail="Storage is required")

        # 创建资产
        result = await AssetService.create_asset(user_id, asset)
        logger.info(f"Asset created successfully: {result}")
        return result
    except Exception as e:
        logger.error(f"Error creating asset: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[AssetResponse])
async def get_assets(
    # user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
    user_id: str = Query(..., description="User ID from authentication"),
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


@router.get("/top-cryptos", response_model=List[Dict])
async def get_top_cryptos(
    # user_id: str = TEMP_USER_ID,
    user_id: str = Query(..., description="User ID from authentication"),
    limit: int = Query(100, description="返回结果数量限制"),
):
    """获取热门加密货币列表"""
    try:
        # 从数据库获取排名靠前的加密货币
        top_cryptos = await CryptocurrencyService.get_top_cryptocurrencies(limit)

        # 转换为前端需要的格式
        result = []
        for crypto in top_cryptos:
            # 获取价格信息
            price = await PriceService.get_crypto_price(crypto.symbol)
            percent_change = await PriceService.get_daily_change(crypto.symbol)

            result.append(
                {
                    "symbol": crypto.symbol,
                    "name": crypto.name,
                    "logo_url": crypto.logo_url,
                    "price": price or 0,
                    "percent_change_24h": percent_change,
                }
            )

        return result
    except Exception as e:
        logger.error(f"Error in get_top_cryptos: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch top cryptocurrencies")


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    # user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
    user_id: str = Query(..., description="User ID from authentication"),
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
    # user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
    user_id: str = Query(..., description="User ID from authentication"),
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
        logger.info(f"Received update request - asset_update: {asset_update.model_dump()}")
        logger.info(f"Request body tokens_holding: {asset_update.tokens_holding}")

        updated_asset = await AssetService.update_asset_by_symbol_and_storage(
            user_id=user_id,
            symbol=asset_update.symbol,
            storage=asset_update.storage,
            asset_update=asset_update,
        )

        if not updated_asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        logger.info(f"Asset updated successfully: {updated_asset.model_dump()}")
        return updated_asset

    except HTTPException:
        raise  # 直接重新抛出 HTTP 异常
    except Exception as e:
        logger.error(f"Error updating asset: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))  # 其他错误才用 400


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    # user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
    user_id: str = Query(..., description="User ID from authentication"),
):
    """删除资产"""
    success = await AssetService.delete_asset(user_id, asset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted successfully"}


@router.post("/update-prices", response_model=List[AssetResponse])
async def update_prices(
    # user_id: str = TEMP_USER_ID,  # 使用固定的 UUID
    user_id: str = Query(..., description="User ID from authentication"),
):
    """更新所有资产的价格"""
    return await AssetService.update_all_prices(user_id)


@router.put("/symbol/{symbol}/storage/{storage}", response_model=AssetResponse)
async def update_asset_by_location(
    symbol: str,
    storage: str,
    asset_update: AssetUpdate,
    # user_id: str = TEMP_USER_ID,
    user_id: str = Query(..., description="User ID from authentication"),
):
    """更新特定交易所的资产数量"""
    asset = await AssetService.update_asset_by_symbol_and_storage(user_id, symbol, storage, asset_update)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("/update-logos", response_model=List[AssetResponse])
async def update_asset_logos(user_id: str = TEMP_USER_ID):
    """更新所有资产的 logo URL"""
    try:
        supabase = db.get_supabase_client()

        # 获取所有资产
        result = supabase.table("assets").select("*").eq("user_id", user_id).execute()
        assets = result.data if result.data else []

        updated_assets = []
        for asset in assets:
            try:
                # 获取 logo URL
                logo_url = await get_crypto_logo(asset["symbol"])

                if logo_url:
                    # 更新资产
                    update_result = (
                        supabase.table("assets").update({"logo_url": logo_url}).eq("id", asset["id"]).execute()
                    )

                    if update_result.data:
                        updated_assets.append(AssetResponse(**update_result.data[0]))
            except Exception as e:
                logger.error(f"Error updating logo for {asset['symbol']}: {str(e)}")
                continue

        return updated_assets
    except Exception as e:
        logger.error(f"Error updating asset logos: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/price/{symbol}", response_model=Dict)
async def get_crypto_price(symbol: str):
    """获取加密货币价格"""
    try:
        price = await PriceService.get_crypto_price(symbol)
        if price is None:
            raise HTTPException(status_code=404, detail=f"Price for {symbol} not found")
        return {"symbol": symbol.upper(), "price": price}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get price for {symbol}")


@router.post("/batch", response_model=List[AssetResponse])
async def create_assets_batch(
    assets: List[Dict],
    # user_id: str = TEMP_USER_ID,
    user_id: str = Query(..., description="User ID from authentication"),
):
    """批量创建资产"""
    try:
        logger.info(f"Received batch create request for {len(assets)} assets")
        created_assets = await AssetService.create_assets_batch(user_id, assets)
        return created_assets
    except Exception as e:
        logger.error(f"Error in batch create assets: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dex/search")
async def search_dex_tokens(query: str = Query(..., min_length=2)):
    """搜索DEX tokens"""
    try:
        results = await DexService.search_tokens(query)
        return results
    except Exception as e:
        logger.error(f"Error searching DEX tokens: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search DEX tokens")


@router.get("/dex/token/{chain}/{token_address}")
async def get_dex_token_info(chain: str, token_address: str):
    """获取DEX token信息"""
    try:
        token_info = await DexService.get_token_info(chain, token_address)
        if not token_info:
            raise HTTPException(status_code=404, detail="Token not found")
        return token_info
    except Exception as e:
        logger.error(f"Error getting DEX token info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get token info")


@router.post("/dex", response_model=AssetResponse)
async def create_dex_token(
    dex_token: dict,
    user_id: str = Query(..., description="User ID from authentication"),
):
    """添加DEX token到用户资产"""
    try:
        # 提取DEX token信息
        symbol = dex_token.get("symbol")
        name = dex_token.get("name")
        tokens_holding = dex_token.get("tokens_holding", 0)
        storage = dex_token.get("storage", "")
        chain = dex_token.get("chain")
        token_address = dex_token.get("token_address")
        logo_url = dex_token.get("logo_url")
        notes = dex_token.get("notes", "")
        purchase_price = dex_token.get("purchase_price")
        created_at = dex_token.get("created_at")

        # 验证必要字段
        if not all([chain, token_address]):
            raise HTTPException(status_code=400, detail="Missing required fields: symbol, chain, or token_address")

        # 检查是否已提供价格信息
        provided_price = dex_token.get("price")
        provided_percent_change = dex_token.get("percent_change_24h")

        # 如果前端没有提供价格信息，才去查询
        if provided_price is None:
            # 获取当前价格
            token_info = await DexService.get_token_info(chain, token_address)
            current_price = token_info.get("price", 0) if token_info else 0
            percent_change_24h = token_info.get("percent_change_24h", 0) if token_info else 0
        else:
            # 使用前端提供的价格信息
            current_price = provided_price
            percent_change_24h = provided_percent_change or 0

        # 创建AssetCreate对象
        from app.schemas.asset import AssetCreate

        asset_create = AssetCreate(
            symbol=symbol,
            tokens_holding=tokens_holding,
            storage=storage,
            asset_type="dex_token",  # 明确设置资产类型为dex_token
            logo_url=logo_url,
            notes=notes,
            purchase_price=purchase_price,
            chain=chain,
            token_address=token_address,
        )

        # 如果提供了created_at，设置到asset_create
        if created_at:
            asset_create.created_at = created_at

        # 添加到数据库 - 这里直接返回了创建的资产对象，不需要再次查询
        created_asset = await AssetService.create_asset(user_id, asset_create)
        return created_asset

    except Exception as e:
        logger.error(f"Error creating DEX token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create DEX token: {str(e)}")


@router.post("/dex/verify", response_model=Dict)
async def verify_dex_token(
    token_data: Dict,
    user_id: str = Query(..., description="User ID from authentication"),
):
    """验证 DEX token 是否有效，但不添加到用户资产"""
    try:
        chain = token_data.get("chain")
        token_address = token_data.get("token_address")

        if not chain or not token_address:
            raise HTTPException(status_code=400, detail="Missing chain or token_address")

        # 尝试获取 token 信息
        token_info = await DexService.get_token_info(chain, token_address)

        if token_info:
            return token_info

        # 如果找不到 token 信息，返回 404
        raise HTTPException(status_code=404, detail="Token not found")

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error verifying DEX token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to verify DEX token: {str(e)}")


@router.get("/dex/token/{chain}/{token_address}/price", response_model=Dict)
async def get_dex_token_price(chain: str, token_address: str):
    """获取DEX token的价格信息"""
    try:
        from app.services.dex import DexService

        # 尝试获取 token 信息，其中包含价格
        token_info = await DexService.get_token_info(chain, token_address)

        if token_info and "price" in token_info:
            # 返回价格信息
            return {"price": token_info["price"], "percent_change_24h": token_info.get("percent_change_24h", 0)}

        # 如果找不到价格信息，返回 404
        raise HTTPException(status_code=404, detail="Price information not found")

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting DEX token price: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get token price")
