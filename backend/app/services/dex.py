import requests
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class DexService:
    BASE_URL = "https://api.dexscreener.com"

    @staticmethod
    async def get_token_info(chain: str, token_address: str) -> Optional[Dict]:
        """获取DEX token信息"""
        try:
            response = requests.get(
                f"{DexService.BASE_URL}/token-pairs/v1/{chain}/{token_address}", headers={}, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                logger.warning(f"No data found for token {token_address} on {chain}")
                return None

            pair = data[0]
            base_token = pair["baseToken"]

            return {
                "name": base_token["name"],
                "symbol": base_token["symbol"],
                "price": float(pair["priceUsd"]) if pair.get("priceUsd") else 0,
                "percent_change_24h": float(pair["priceChange"]["h24"])
                if pair.get("priceChange", {}).get("h24")
                else 0,
                "logo_url": pair.get("info", {}).get("imageUrl"),
                "chain": chain,
                "token_address": token_address,
                "asset_type": "dex_token",
            }

        except Exception as e:
            logger.error(f"Error fetching DEX token info: {str(e)}")
            return None

    @staticmethod
    async def search_tokens(query: str) -> List[Dict]:
        """搜索DEX tokens"""
        try:
            response = requests.get(f"{DexService.BASE_URL}/latest/dex/search", params={"query": query}, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = []
            for pair in data.get("pairs", []):
                base_token = pair["baseToken"]
                results.append(
                    {
                        "name": base_token["name"],
                        "symbol": base_token["symbol"],
                        "price": float(pair["priceUsd"]) if pair.get("priceUsd") else 0,
                        "percent_change_24h": float(pair["priceChange"]["h24"])
                        if pair.get("priceChange", {}).get("h24")
                        else 0,
                        "logo_url": pair.get("info", {}).get("imageUrl"),
                        "chain": pair["chainId"],
                        "token_address": base_token["address"],
                        "asset_type": "dex_token",
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error searching DEX tokens: {str(e)}")
            return []
