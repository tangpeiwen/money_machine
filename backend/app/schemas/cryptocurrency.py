from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class CryptocurrencyBase(BaseModel):
    """加密货币基本信息模型"""

    symbol: str
    name: str
    logo_url: Optional[str] = None
    rank: Optional[int] = None


class CryptocurrencyCreate(CryptocurrencyBase):
    """创建加密货币模型"""

    pass


class CryptocurrencyUpdate(BaseModel):
    """更新加密货币模型"""

    name: Optional[str] = None
    logo_url: Optional[str] = None
    rank: Optional[int] = None


class CryptocurrencyInDB(CryptocurrencyBase):
    """数据库中的加密货币模型"""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CryptocurrencyResponse(CryptocurrencyBase):
    """API响应的加密货币模型"""

    id: UUID

    class Config:
        from_attributes = True
