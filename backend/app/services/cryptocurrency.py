from typing import List, Dict, Optional
import logging
from datetime import datetime
import uuid

from ..core.config import settings
from ..core.database import db
from ..schemas.cryptocurrency import CryptocurrencyCreate, CryptocurrencyInDB, CryptocurrencyUpdate

logger = logging.getLogger(__name__)


class CryptocurrencyService:
    """加密货币数据服务"""

    @staticmethod
    async def get_cryptocurrency(symbol: str) -> Optional[CryptocurrencyInDB]:
        """通过符号获取加密货币信息"""
        try:
            supabase = db.get_supabase_client()
            result = supabase.table("cryptocurrencies").select("*").eq("symbol", symbol.upper()).execute()

            if result.data and len(result.data) > 0:
                return CryptocurrencyInDB(**result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting cryptocurrency {symbol}: {e}")
            return None

    @staticmethod
    async def create_cryptocurrency(crypto: CryptocurrencyCreate) -> CryptocurrencyInDB:
        """创建新的加密货币记录"""
        try:
            supabase = db.get_supabase_client()

            # 查询当前最大的 rank
            max_rank_result = supabase.table("cryptocurrencies").select("rank").order("rank.desc").limit(1).execute()
            max_rank = 0
            if max_rank_result.data and len(max_rank_result.data) > 0:
                max_rank = max_rank_result.data[0].get("rank", 0) or 0

            # 准备数据
            now = datetime.utcnow()
            crypto_data = {
                "id": str(uuid.uuid4()),
                "symbol": crypto.symbol.upper(),
                "name": crypto.name,
                "logo_url": crypto.logo_url,
                "rank": max_rank + 1,  # 分配新的 rank
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            # 插入数据
            result = supabase.table("cryptocurrencies").insert(crypto_data).execute()

            if not result.data:
                raise ValueError("Failed to insert cryptocurrency into database")

            return CryptocurrencyInDB(**result.data[0])
        except Exception as e:
            logger.error(f"Error creating cryptocurrency: {e}")
            raise

    @staticmethod
    async def update_cryptocurrency(symbol: str, crypto_update: CryptocurrencyUpdate) -> Optional[CryptocurrencyInDB]:
        """更新加密货币信息"""
        try:
            supabase = db.get_supabase_client()

            # 准备更新数据
            update_data = {k: v for k, v in crypto_update.dict().items() if v is not None}
            update_data["updated_at"] = datetime.utcnow().isoformat()

            # 更新数据
            result = supabase.table("cryptocurrencies").update(update_data).eq("symbol", symbol.upper()).execute()

            if result.data and len(result.data) > 0:
                return CryptocurrencyInDB(**result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating cryptocurrency {symbol}: {e}")
            return None

    @staticmethod
    async def search_cryptocurrency(query: str, limit: int = 10) -> List[CryptocurrencyInDB]:
        """
        搜索加密货币（模糊匹配 symbol 和 name）

        Args:
            query: 搜索关键词
            limit: 返回结果数量限制

        Returns:
            匹配的加密货币列表
        """
        try:
            if not query or len(query.strip()) < 2:
                return []

            query = query.strip().upper()
            supabase = db.get_supabase_client()

            # 在本地数据库中搜索
            # 使用 ilike 进行模糊匹配，同时匹配 symbol 和 name
            result = (
                supabase.table("cryptocurrencies")
                .select("*")
                .or_(f"symbol.ilike.%{query}%,name.ilike.%{query}%")
                .order("rank")
                .limit(limit)
                .execute()
            )

            # 如果找到结果，返回
            if result.data and len(result.data) > 0:
                return [CryptocurrencyInDB(**item) for item in result.data]

            # 如果没有结果，返回空列表
            return []

        except Exception as e:
            logger.error(f"Error searching cryptocurrencies: {e}")
            return []

    @staticmethod
    async def get_top_cryptocurrencies(limit: int = 100) -> List[CryptocurrencyInDB]:
        """获取排名靠前的加密货币"""
        try:
            supabase = db.get_supabase_client()

            # 按照 rank 排序获取前 N 个加密货币
            result = supabase.table("cryptocurrencies").select("*").order("rank").limit(limit).execute()

            return [CryptocurrencyInDB(**item) for item in result.data]
        except Exception as e:
            logger.error(f"Error getting top cryptocurrencies: {e}")
            return []
