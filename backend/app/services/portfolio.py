from typing import Optional, Dict, List, Any
import logging

from ..core.database import db
from ..schemas.portfolio import AssetCreate, AssetUpdate, PortfolioResponse
from datetime import datetime
from .history import HistoryService
from .asset import AssetService
from ..core.utils import get_crypto_logo

# 设置日志记录器
logger = logging.getLogger(__name__)


class PortfolioService:
    @staticmethod
    async def get_portfolio(user_id: str) -> Optional[PortfolioResponse]:
        """获取用户的投资组合"""
        supabase = db.get_supabase_client()

        # 获取最新日期的汇总数据
        result = (
            supabase.table("portfolio_history")
            .select("*")
            .eq("user_id", user_id)
            .order("date", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        latest_date = result.data[0]["date"]

        # 获取最新日期的所有资产数据
        assets_result = (
            supabase.table("portfolio_history").select("*").eq("user_id", user_id).eq("date", latest_date).execute()
        )

        if not assets_result.data:
            return None

        # 计算总价值
        total_value = sum(asset.get("holding_value", 0) for asset in assets_result.data)

        # 处理资产数据，转换为前端需要的格式
        assets_with_data = []
        for asset in assets_result.data:
            # 获取每个加密货币的24小时价格变化
            # daily_change = await PriceService.get_daily_change(asset.get("symbol"))

            assets_with_data.append(
                {
                    "name": asset.get("name"),
                    "symbol": asset.get("symbol"),
                    "amount": asset.get("tokens_holding"),
                    "value": asset.get("holding_value", 0),
                    "percent_change_24h": asset.get("percent_change_24h", 0),  # 确保这个字段存在
                    "logo_url": asset.get("logo_url"),  # 添加 logo_url 字段
                }
            )
            logger.info(f"Processed asset data: {assets_with_data}")

        return PortfolioResponse(
            user_id=user_id, assets=assets_with_data, total_value=total_value, last_updated=latest_date
        )

    @staticmethod
    async def create_portfolio(user_id: str) -> PortfolioResponse:
        """创建新的投资组合（实际上只是返回空的投资组合，因为资产是单独添加的）"""
        return PortfolioResponse(user_id=user_id, assets=[], total_value=0, last_updated=None)

    @staticmethod
    async def add_asset(user_id: str, asset: AssetCreate) -> PortfolioResponse:
        """添加新资产到投资组合"""
        supabase = db.get_supabase_client()

        # 获取当前价格、涨跌幅和计算价值
        crypto_info = await AssetService.get_crypto_info(asset.symbol)
        current_price = crypto_info["price"] if crypto_info else 0
        percent_change_24h = crypto_info["percent_change_24h"] if crypto_info else 0
        holding_value = current_price * asset.tokens_holding

        # 1. 添加到 assets 表
        asset_data = {
            "user_id": user_id,
            **asset.model_dump(),
            "current_price": current_price,
            "holding_value": holding_value,
            "percent_change_24h": percent_change_24h,  # 添加涨跌幅
            "logo_url": await get_crypto_logo(asset.symbol),  # 添加 logo_url
        }
        supabase.table("assets").insert(asset_data).execute()

        # 2. 创建历史记录
        await HistoryService.record_portfolio_snapshot(user_id)

        return await PortfolioService.get_portfolio(user_id)

    @staticmethod
    async def record_portfolio_snapshot(user_id: str):
        """更新投资组合历史记录"""
        supabase = db.get_supabase_client()

        # 1. 获取用户所有资产
        assets_result = supabase.table("assets").select("*").eq("user_id", user_id).execute()

        # 2. 按 symbol 汇总资产
        symbol_totals = {}
        for asset in assets_result.data:
            symbol = asset["symbol"]
            if symbol not in symbol_totals:
                symbol_totals[symbol] = {
                    "tokens_holding": 0,
                    "current_price": asset["current_price"],
                    "percent_change_24h": asset["percent_change_24h"],  # 添加涨跌幅
                }
            symbol_totals[symbol]["tokens_holding"] += asset["tokens_holding"]

        # 3. 插入新的历史记录
        history_records = []
        for symbol, data in symbol_totals.items():
            tokens_holding = data["tokens_holding"]
            current_price = data["current_price"]
            history_records.append(
                {
                    "user_id": user_id,
                    "symbol": symbol,
                    "tokens_holding": tokens_holding,
                    "current_price": current_price,
                    "holding_value": current_price * tokens_holding,
                    "percent_change_24h": data["percent_change_24h"],  # 添加涨跌幅
                    "date": datetime.now().isoformat(),
                }
            )

        if history_records:
            supabase.table("portfolio_history").insert(history_records).execute()

    @staticmethod
    async def update_asset(user_id: str, symbol: str, asset_update: AssetUpdate) -> PortfolioResponse:
        """更新资产信息"""
        supabase = db.get_supabase_client()

        # 获取当前价格和涨跌幅
        crypto_info = await AssetService.get_crypto_info(symbol)
        current_price = crypto_info["price"] if crypto_info else 0
        percent_change_24h = crypto_info["percent_change_24h"] if crypto_info else 0

        # 计算新的持仓价值
        holding_value = current_price * asset_update.amount

        # 插入新的历史记录
        result = (
            supabase.table("portfolio_history")
            .insert(
                {
                    "user_id": user_id,
                    "symbol": symbol,
                    "current_price": current_price,
                    "tokens_holding": asset_update.amount,
                    "holding_value": holding_value,
                    "percent_change_24h": percent_change_24h,  # 添加涨跌幅
                    "logo_url": await get_crypto_logo(symbol),  # 添加 logo_url
                    "date": datetime.now().isoformat(),
                }
            )
            .execute()
        )

        # 返回更新后的投资组合
        return await PortfolioService.get_portfolio(user_id)
