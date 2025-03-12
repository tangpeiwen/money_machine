from typing import List, Optional, Dict
from ..core.database import db
from ..schemas.asset import AssetCreate, AssetUpdate, AssetInDB
from .price import PriceService
from .history import HistoryService
from ..core.utils import get_crypto_logo
from datetime import datetime
from .dex import DexService


import logging

# 设置日志记录器
logger = logging.getLogger(__name__)


class AssetService:
    @staticmethod
    async def create_asset(user_id: str, asset: AssetCreate) -> AssetInDB:
        """创建新资产"""
        try:
            logger.info(f"Creating asset for user {user_id}: {asset}")
            supabase = db.get_supabase_client()

            # 根据资产类型获取信息
            if asset.asset_type == "dex_token":
                if not asset.chain or not asset.token_address:
                    raise ValueError("Chain and token_address are required for DEX tokens")

                crypto_info = await DexService.get_token_info(asset.chain, asset.token_address)
                if not crypto_info:
                    raise ValueError(f"无法获取DEX token信息: {asset.symbol}")
            else:
                crypto_info = await PriceService.get_crypto_info(asset.symbol)
                if not crypto_info:
                    raise ValueError(f"无法获取加密货币信息: {asset.symbol}")

            logger.info(f"Got crypto info: {crypto_info}")

            # 计算持仓价值
            holding_value = asset.tokens_holding * crypto_info["price"]

            # 准备插入数据
            asset_data = {
                "user_id": user_id,
                "name": crypto_info["name"],
                "symbol": asset.symbol.upper(),
                "storage": asset.storage,
                "tokens_holding": asset.tokens_holding,
                "current_price": crypto_info["price"],
                "holding_value": holding_value,
                "percent_change_24h": crypto_info.get("percent_change_24h", 0),
                "asset_type": asset.asset_type,
                "logo_url": crypto_info.get("logo_url")
                if asset.asset_type == "dex_token"
                else await get_crypto_logo(asset.symbol.upper()),
                "token_address": asset.token_address,
                # 添加新字段
                "notes": asset.notes,
                "purchase_price": asset.purchase_price if asset.purchase_price is not None else crypto_info["price"],
                # 如果前端提供了创建时间，则使用前端提供的，否则使用当前时间
                "created_at": asset.created_at if hasattr(asset, "created_at") and asset.created_at else None,
            }

            logger.info(f"Inserting asset data: {asset_data}")

            # 插入数据
            result = supabase.table("assets").insert(asset_data).execute()

            if not result.data:
                raise ValueError("Failed to insert asset into database")

            logger.info(f"Asset created successfully: {result.data[0]}")
            return AssetInDB(**result.data[0])

        except Exception as e:
            logger.error(f"Error in create_asset: {str(e)}")
            raise

    @staticmethod
    async def get_assets(user_id: str) -> List[AssetInDB]:
        """获取用户的所有资产"""
        try:
            supabase = db.get_supabase_client()
            result = supabase.table("assets").select("*").eq("user_id", user_id).execute()

            logger.info(f"Raw result from database: {result.data}")

            if not result.data:
                return []

            assets = []
            for asset_data in result.data:
                try:
                    asset = AssetInDB(**asset_data)
                    assets.append(asset)
                except Exception as e:
                    logger.error(f"Error parsing asset data: {asset_data}")
                    logger.error(f"Error details: {str(e)}")
                    continue

            return assets

        except Exception as e:
            logger.error(f"Error in get_assets: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def get_asset(user_id: str, asset_id: str) -> Optional[AssetInDB]:
        """获取单个资产详情"""
        supabase = db.get_supabase_client()
        result = supabase.table("assets").select("*").eq("user_id", user_id).eq("id", asset_id).execute()
        return AssetInDB(**result.data[0]) if result.data else None

    @staticmethod
    async def update_asset(user_id: str, asset_id: str, asset_update: AssetUpdate) -> Optional[AssetInDB]:
        """更新资产信息"""
        supabase = db.get_supabase_client()

        # 获取现有资产信息
        asset = await AssetService.get_asset(user_id, asset_id)
        if not asset:
            return None

        # 准备更新数据
        update_data = {k: v for k, v in asset_update.model_dump().items() if v is not None}

        # 获取最新价格并更新价值
        if "tokens_holding" in update_data:
            crypto_info = await PriceService.get_crypto_info(asset.symbol)
            if crypto_info:
                update_data.update(
                    {
                        "current_price": crypto_info["price"],
                        "holding_value": crypto_info["price"] * update_data["tokens_holding"],
                        "percent_change_24h": crypto_info["percent_change_24h"],
                    }
                )

        result = supabase.table("assets").update(update_data).eq("user_id", user_id).eq("id", asset_id).execute()
        return AssetInDB(**result.data[0]) if result.data else None

    @staticmethod
    async def delete_asset(user_id: str, asset_id: str) -> bool:
        """删除资产"""
        supabase = db.get_supabase_client()
        result = supabase.table("assets").delete().eq("user_id", user_id).eq("id", asset_id).execute()
        return bool(result.data)

    @staticmethod
    async def update_all_prices(user_id: str) -> List[AssetInDB]:
        """更新所有资产的价格"""
        assets = await AssetService.get_assets(user_id)
        supabase = db.get_supabase_client()

        updated_assets = []
        for asset in assets:
            try:
                # 根据资产类型选择不同的价格更新方法
                if asset.asset_type == "dex_token":
                    # 对于DEX token，使用DexService获取价格
                    if not asset.chain or not asset.token_address:
                        logger.warning(f"Missing chain or token_address for DEX token: {asset.symbol}")
                        continue

                    crypto_info = await DexService.get_token_info(asset.chain, asset.token_address)
                else:
                    # 对于普通加密货币，使用PriceService获取价格
                    crypto_info = await PriceService.get_crypto_info(asset.symbol)

                if crypto_info:
                    # 更新 assets 表
                    result = (
                        supabase.table("assets")
                        .update(
                            {
                                "name": crypto_info["name"],
                                "current_price": crypto_info["price"],
                                "holding_value": crypto_info["price"] * asset.tokens_holding,
                                "percent_change_24h": crypto_info["percent_change_24h"],
                            }
                        )
                        .eq("id", asset.id)
                        .execute()
                    )

                    if result.data:
                        updated_assets.append(AssetInDB(**result.data[0]))
            except Exception as e:
                logger.error(f"Error updating price for asset {asset.symbol}: {str(e)}")
                continue

        # 更新完所有资产后，创建新的历史记录
        await HistoryService.record_portfolio_snapshot(user_id)

        return updated_assets

    @staticmethod
    async def get_asset_by_symbol_and_storage(user_id: str, symbol: str, storage: str) -> Optional[AssetInDB]:
        """获取特定交易所的资产"""
        supabase = db.get_supabase_client()
        result = (
            supabase.table("assets")
            .select("*")
            .eq("user_id", user_id)
            .eq("symbol", symbol)
            .eq("storage", storage)
            .execute()
        )

        return AssetInDB(**result.data[0]) if result.data else None

    @staticmethod
    async def update_asset_by_symbol_and_storage(
        user_id: str, symbol: str, storage: str, asset_update: AssetUpdate
    ) -> Optional[AssetInDB]:
        """更新特定交易所的资产数量"""
        logger.info(f"Updating asset: user_id={user_id}, symbol={symbol}, storage={storage}")

        supabase = db.get_supabase_client()

        # 获取现有资产
        try:
            result = (
                supabase.table("assets")
                .select("*")
                .eq("user_id", user_id)
                .eq("symbol", symbol)
                .eq("storage", storage)
                .execute()
            )

            logger.info(f"Query result: {result.data}")

            if not result.data:
                logger.error(f"Asset not found: symbol={symbol}, storage={storage}")
                return None

            asset = AssetInDB(**result.data[0])
            logger.info(f"Found existing asset: {asset}")

            # 准备更新数据
            update_data = {k: v for k, v in asset_update.model_dump().items() if v is not None}
            logger.info(f"Update data prepared: {update_data}")

            # 如果更新数量，重新计算价值
            if "tokens_holding" in update_data:
                crypto_info = await PriceService.get_crypto_info(symbol)
                if crypto_info:
                    update_data.update(
                        {
                            "current_price": crypto_info["price"],
                            "holding_value": crypto_info["price"] * update_data["tokens_holding"],
                        }
                    )
                    logger.info(f"Updated price info: {crypto_info}")

            # 更新资产
            result = (
                supabase.table("assets")
                .update(update_data)
                .eq("user_id", user_id)
                .eq("symbol", symbol)
                .eq("storage", storage)
                .execute()
            )

            if not result.data:
                logger.error("Failed to update asset in database")
                return None

            logger.info(f"Asset updated successfully: {result.data[0]}")

            # 更新完资产后，创建新的历史记录
            await HistoryService.record_portfolio_snapshot(user_id)
            logger.info("Portfolio history updated")

            return AssetInDB(**result.data[0])

        except Exception as e:
            logger.error(f"Error in update_asset_by_symbol_and_storage: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def create_assets_batch(user_id: str, assets_data: List[Dict]) -> List[AssetInDB]:
        """批量创建资产

        参数:
        - user_id: 用户ID
        - assets_data: 资产数据列表，每个元素包含:
            - symbol: 资产符号
            - amount: 持有数量
            - storage: 存储位置
            - current_price: 当前价格（从截图识别获取）
            - name: 资产名称（从截图识别获取）

        返回:
        - 创建的资产列表
        """
        try:
            supabase = db.get_supabase_client()
            current_time = datetime.utcnow().isoformat()

            # 准备批量插入的数据
            batch_data = []
            for asset_data in assets_data:
                # 计算持仓价值
                holding_value = asset_data["amount"] * asset_data.get("current_price", 0)

                asset_insert = {
                    "user_id": user_id,
                    "symbol": asset_data["symbol"].upper(),
                    "name": asset_data.get("name", asset_data["symbol"]),  # 如果没有名称，使用symbol
                    "storage": asset_data["storage"],
                    "tokens_holding": asset_data["amount"],
                    "current_price": asset_data.get("current_price", 0),
                    "holding_value": holding_value,
                    "percent_change_24h": asset_data.get("percent_change_24h", 0),
                    "asset_type": asset_data.get("asset_type", "cryptocurrency"),
                    "logo_url": await get_crypto_logo(asset_data["symbol"].upper()),
                    # "created_at": current_time,
                    "updated_at": current_time,
                }
                batch_data.append(asset_insert)

            # 批量插入数据
            if batch_data:
                result = supabase.table("assets").insert(batch_data).execute()
                if result.data:
                    return [AssetInDB(**asset) for asset in result.data]

            return []

        except Exception as e:
            logger.error(f"Error in create_assets_batch: {str(e)}")
            logger.error(f"Batch data: {batch_data}")
            raise
