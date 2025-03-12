import requests
import logging
from ..core.config import settings
import uuid


def generate_uuid() -> str:
    """生成 UUID 字符串"""
    return str(uuid.uuid4())


logger = logging.getLogger(__name__)

# 常量定义
TEMP_USER_ID = "123e4567-e89b-12d3-a456-426614174000"


async def get_crypto_logo(symbol: str) -> str:
    """从 CoinMarketCap 获取加密货币的 logo URL"""
    try:
        url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/info"
        params = {"symbol": symbol}
        headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": settings.CMC_API_KEY}

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if data.get("data") and data["data"].get(symbol):
            return data["data"][symbol][0]["logo"]
    except Exception as e:
        logger.error(f"Error fetching logo for {symbol}: {str(e)}")

    return None
