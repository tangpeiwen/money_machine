from typing import List, Optional
from ..core.database import db
from ..schemas.asset import AssetCreate, AssetUpdate, AssetInDB
from .price import PriceService
from .history import HistoryService
import logging

# 设置日志记录器
logger = logging.getLogger(__name__)


class AssetService:
    @staticmethod
    async def create_asset(user_id: str, asset: AssetCreate) -> AssetInDB:
        """创建新资产"""
        supabase = db.get_supabase_client()

        # 获取加密货币信息
        crypto_info = await PriceService.get_crypto_info(asset.symbol)
        if not crypto_info:
            raise ValueError(f"无法获取加密货币信息: {asset.symbol}")

        # 准备插入数据
        asset_data = {
            "user_id": user_id,
            "name": crypto_info["name"],
            "symbol": crypto_info["symbol"],
            "storage": asset.storage,
            "asset_type": "cryptocurrency",
            "current_price": crypto_info["price"],
            "tokens_holding": asset.tokens_holding,
            "holding_value": crypto_info["price"] * asset.tokens_holding,
            "percent_change_24h": crypto_info["percent_change_24h"],
        }

        # 插入数据并返回结果
        result = supabase.table("assets").insert(asset_data).execute()
        return AssetInDB(**result.data[0])

    @staticmethod
    async def get_assets(user_id: str) -> List[AssetInDB]:
        """获取用户的所有资产"""
        supabase = db.get_supabase_client()
        result = supabase.table("assets").select("*").eq("user_id", user_id).execute()
        return [AssetInDB(**asset) for asset in result.data]

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
