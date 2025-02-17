import requests
from typing import Optional, Dict
from ..core.config import settings
import aiohttp


class PriceService:
    @staticmethod
    async def get_crypto_info(symbol: str) -> Optional[Dict]:
        """获取加密货币详细信息
        Args:
            symbol: 加密货币代号（如 BTC, ETH）
        Returns:
            dict: 包含名称、价格等信息的字典，如果获取失败则返回 None
        """
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        params = {"symbol": symbol.upper(), "convert": "USD"}
        headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": settings.CMC_API_KEY}

        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            if "data" in data and data["data"]:
                crypto_data = data["data"][symbol.upper()]
                return {
                    "name": crypto_data["name"],
                    "symbol": crypto_data["symbol"],
                    "price": crypto_data["quote"]["USD"]["price"],
                }

        except Exception as e:
            print(f"获取价格时出错: {str(e)}")  # TODO: 使用proper日志记录

        return None

    @staticmethod
    async def get_crypto_price(symbol: str) -> Optional[float]:
        """获取加密货币当前价格
        Args:
            symbol: 加密货币代号（如 BTC, ETH）
        Returns:
            float: 当前价格，如果获取失败则返回 None
        """
        info = await PriceService.get_crypto_info(symbol)
        return info["price"] if info else None


class PriceService:
    @staticmethod
    async def get_crypto_info(symbol: str) -> Optional[Dict]:
        """获取加密货币详细信息
        Args:
            symbol: 加密货币代号（如 BTC, ETH）
        Returns:
            dict: 包含名称、价格等信息的字典，如果获取失败则返回 None
        """
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        params = {"symbol": symbol.upper(), "convert": "USD"}
        headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": settings.CMC_API_KEY}

        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            if "data" in data and data["data"]:
                crypto_data = data["data"][symbol.upper()]
                return {
                    "name": crypto_data["name"],
                    "symbol": crypto_data["symbol"],
                    "price": crypto_data["quote"]["USD"]["price"],
                }

        except Exception as e:
            print(f"获取价格时出错: {str(e)}")  # TODO: 使用proper日志记录

        return None

    @staticmethod
    async def get_daily_change(symbol: str) -> float:
        """获取加密货币的24小时价格变化百分比"""
        try:
            from ..core.database import db

            supabase = db.get_supabase_client()

            # 获取最近两天的历史数据
            result = (
                supabase.table("portfolio_history")
                .select("*")
                .eq("symbol", symbol.upper())
                .order("date", desc=True)
                .limit(2)
                .execute()
            )

            if len(result.data) >= 2:
                current_price = result.data[0]["current_price"]
                previous_price = result.data[1]["current_price"]

                if previous_price > 0:
                    percent_change = ((current_price - previous_price) / previous_price) * 100
                    return round(percent_change, 2)

            # 如果没有足够的历史数据，尝试使用 CoinMarketCap API
            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
            params = {"symbol": symbol.upper(), "convert": "USD"}
            headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": settings.CMC_API_KEY}

            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            if "data" in data and data["data"]:
                crypto_data = data["data"][symbol.upper()]
                return round(crypto_data["quote"]["USD"]["percent_change_24h"], 2)

            return 0

        except Exception as e:
            print(f"Error getting daily change for {symbol}: {e}")
            return 0
