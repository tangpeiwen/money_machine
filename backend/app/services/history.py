from typing import List, Optional, Dict
from datetime import datetime
from collections import defaultdict
from ..core.database import db
from ..schemas.asset import AssetInDB
from .price import PriceService


class HistoryService:
    @staticmethod
    async def record_portfolio_snapshot(user_id: str) -> bool:
        """记录投资组合快照，每个日期每个币种只保留最新记录"""
        supabase = db.get_supabase_client()
        today = datetime.utcnow().date().isoformat()

        # 获取资产数据
        result = supabase.table("assets").select("*").eq("user_id", user_id).execute()
        assets = result.data if result.data else []

        # 按币种汇总数据
        symbol_totals = defaultdict(lambda: {"tokens_holding": 0, "holding_value": 0, "percent_change_24h": 0})

        # 记录当前拥有的所有币种
        current_symbols = set()

        for asset in assets:
            symbol = asset["symbol"]
            current_symbols.add(symbol)
            symbol_totals[symbol]["tokens_holding"] += asset["tokens_holding"]
            symbol_totals[symbol]["holding_value"] += asset["holding_value"]
            symbol_totals[symbol]["current_price"] = asset["current_price"]
            symbol_totals[symbol]["asset_type"] = asset["asset_type"]
            symbol_totals[symbol]["percent_change_24h"] = asset["percent_change_24h"]
            symbol_totals[symbol]["logo_url"] = asset["logo_url"]

        # 1. 先删除今天已经不存在的资产记录
        existing_result = (
            supabase.table("portfolio_history").select("symbol").eq("user_id", user_id).eq("date", today).execute()
        )

        if existing_result.data:
            existing_symbols = {record["symbol"] for record in existing_result.data}
            symbols_to_delete = existing_symbols - current_symbols

            if symbols_to_delete:
                supabase.table("portfolio_history").delete().eq("user_id", user_id).eq("date", today).in_(
                    "symbol", list(symbols_to_delete)
                ).execute()

        # 2. 更新或插入当前资产记录
        for symbol, totals in symbol_totals.items():
            result = (
                supabase.table("portfolio_history")
                .upsert(
                    {
                        "user_id": user_id,
                        "symbol": symbol,
                        "asset_type": totals["asset_type"],
                        "current_price": totals["current_price"],
                        "tokens_holding": totals["tokens_holding"],
                        "holding_value": totals["holding_value"],
                        "percent_change_24h": totals["percent_change_24h"],
                        "logo_url": totals["logo_url"],
                        "date": today,
                    },
                    on_conflict="user_id,symbol,date",
                )
                .execute()
            )

        return True

    @staticmethod
    async def get_portfolio_history(
        user_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[dict]:
        """获取投资组合历史记录
        Args:
            user_id: 用户ID
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
        Returns:
            List[dict]: 历史记录列表
        """
        supabase = db.get_supabase_client()
        query = supabase.table("portfolio_history").select("*").eq("user_id", user_id)

        if start_date:
            query = query.gte("date", start_date.isoformat())
        if end_date:
            query = query.lte("date", end_date.isoformat())

        result = query.order("date", desc=True).execute()
        return result.data if result.data else []

    @staticmethod
    async def get_asset_history(
        user_id: str, symbol: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[dict]:
        """获取单个资产的历史记录
        Args:
            user_id: 用户ID
            symbol: 资产代号
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
        Returns:
            List[dict]: 历史记录列表
        """
        supabase = db.get_supabase_client()
        query = supabase.table("portfolio_history").select("*").eq("user_id", user_id).eq("symbol", symbol.upper())

        if start_date:
            query = query.gte("date", start_date.isoformat())
        if end_date:
            query = query.lte("date", end_date.isoformat())

        result = query.order("date", desc=True).execute()
        return result.data if result.data else []

    @staticmethod
    async def calculate_portfolio_stats(user_id: str) -> dict:
        """计算投资组合统计数据，基于汇总后的历史数据
        Returns:
            dict: 包含总值、24小时变化等信息
        """
        supabase = db.get_supabase_client()

        # 获取当前资产汇总数据
        result = supabase.table("assets").select("*").eq("user_id", user_id).execute()
        current_assets = result.data if result.data else []

        # 按币种汇总当前数据
        current_totals = defaultdict(lambda: {"tokens_holding": 0, "holding_value": 0})
        for asset in current_assets:
            current_totals[asset["symbol"]]["tokens_holding"] += asset["tokens_holding"]
            current_totals[asset["symbol"]]["holding_value"] += asset["holding_value"]

        # 计算当前总值
        total_value = sum(totals["holding_value"] for totals in current_totals.values())

        # 获取24小时前的历史记录
        yesterday = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        history_result = (
            supabase.table("portfolio_history")
            .select("*")
            .eq("user_id", user_id)
            .gte("date", yesterday.isoformat())
            .execute()
        )
        history_records = history_result.data if history_result.data else []

        # 计算每个币种的变化
        symbol_changes = {}
        old_total_value = 0

        for record in history_records:
            symbol = record["symbol"]
            old_value = record["holding_value"]
            old_total_value += old_value

            current_value = current_totals[symbol]["holding_value"]
            value_change = current_value - old_value
            percent_change = (value_change / old_value * 100) if old_value > 0 else 0

            symbol_changes[symbol] = {
                "value_change": value_change,
                "percent_change": percent_change,
                "old_value": old_value,
                "current_value": current_value,
            }

        # 计算总体变化
        value_change_24h = total_value - old_total_value
        # percent_change_24h = (value_change_24h / old_total_value * 100) if old_total_value > 0 else 0

        return {
            "total_value": total_value,
            "value_change_24h": value_change_24h,
            # "percent_change_24h": percent_change_24h,
            "asset_count": len(current_totals),
            "last_updated": datetime.utcnow().isoformat(),
            "symbol_changes": symbol_changes,
        }
