import requests
from typing import Optional, Dict
from api_service.utils.logger import logger


class DexService:
    """处理 DexScreener API 相关的服务"""

    def __init__(self):
        self.base_url = "https://api.dexscreener.com"

    def get_token_info(self, chain: str, token_address: str) -> Optional[Dict]:
        """
        获取代币价格和基本信息

        Args:
            chain: 链名称 (例如: 'solana', 'ethereum', 'bsc')
            token_address: 代币合约地址

        Returns:
            dict: 包含价格、名称和符号的字典，如果获取失败返回 None
        """
        try:
            url = f"{self.base_url}/token-pairs/v1/{chain}/{token_address}"
            logger.info(f"请求 DexScreener API: {url}")

            response = requests.get(url)
            logger.info(f"DexScreener API 响应状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                if data and data[0].get("priceUsd"):
                    base_token = data[0].get("baseToken", {})
                    return {
                        "price": float(data[0]["priceUsd"]),
                        "name": base_token.get("name", ""),
                        "symbol": base_token.get("symbol", ""),
                    }

            return None

        except Exception as e:
            logger.error(f"从 DexScreener 获取代币信息时出错: {str(e)}")
            return None
