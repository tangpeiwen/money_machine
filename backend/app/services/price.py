import requests
from typing import Optional, Dict

# import aiohttp
import logging

from ..core.config import settings


logger = logging.getLogger(__name__)


class PriceService:
    @staticmethod
    async def get_crypto_info(symbol: str) -> Optional[Dict]:
        """获取加密货币详细信息
        Args:
            symbol: 加密货币代号（如 BTC, ETH）
        Returns:
            dict: 包含名称、价格等信息的字典，如果获取失败则返回 None
        """
        # Special handling for USDT - always return $1 with 0% change
        if symbol.upper() == "USDT":
            return {
                "name": "Tether",
                "symbol": "USDT",
                "price": 1.0,
                "percent_change_1h": 0.0,
                "percent_change_24h": 0.0,
                "percent_change_7d": 0.0,
            }

        url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"
        params = {"symbol": symbol.upper(), "convert": "USD"}
        headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": settings.CMC_API_KEY}

        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            if "data" in data and data["data"]:
                crypto_data = data["data"][symbol.upper()][0]
                return {
                    "name": crypto_data["name"],
                    "symbol": crypto_data["symbol"],
                    "price": crypto_data["quote"]["USD"]["price"],
                    "percent_change_1h": crypto_data["quote"]["USD"]["percent_change_1h"],
                    "percent_change_24h": crypto_data["quote"]["USD"]["percent_change_24h"],
                    "percent_change_7d": crypto_data["quote"]["USD"]["percent_change_7d"],
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

    @staticmethod
    async def get_daily_change(symbol: str) -> float:
        """获取加密货币的24小时价格变化百分比"""
        # Special handling for USDT - always return 0% change
        if symbol.upper() == "USDT":
            return 0.0

        try:
            url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"
            params = {"symbol": symbol.upper(), "convert": "USD"}
            headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": settings.CMC_API_KEY}

            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            if "data" in data and data["data"]:
                crypto_data = data["data"][symbol.upper()][0]
                return round(crypto_data["quote"]["USD"]["percent_change_24h"], 2)

            return 0

        except Exception as e:
            print(f"Error getting daily change for {symbol}: {e}")
            return 0
