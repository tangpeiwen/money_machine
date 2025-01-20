import requests
from typing import Dict, Any

from api_service.config import settings
from api_service.utils.logger import logger


class CryptoService:
    @staticmethod
    def get_crypto_price(query: str, query_type: str = "symbol") -> Dict[str, Any]:
        """获取加密货币价格信息
        Args:
            query: 搜索词（可以是 symbol 或 name）
            query_type: 'symbol' 或 'slug'，表示搜索类型
        """
        logger.info(f"正在获取加密货币信息，搜索类型: {query_type}, 搜索词: {query}")

        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        parameters = {query_type: query.lower() if query_type == "slug" else query.upper(), "convert": "USD"}
        headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": settings.CMC_API_KEY}

        try:
            response = requests.get(url, headers=headers, params=parameters)
            data = response.json()

            if "data" in data and data["data"]:
                crypto_data = list(data["data"].values())[0]
                result = {
                    "name": crypto_data["name"],
                    "symbol": crypto_data["symbol"],
                    "price": crypto_data["quote"]["USD"]["price"],
                    "success": True,
                }
                logger.info(f"成功获取价格数据: {result}")
                return result

            logger.warning(f"未找到匹配的加密货币: {query}")

        except Exception as e:
            logger.error(f"获取加密货币信息时出错: {e}")
            logger.exception(e)

        return {"success": False}
