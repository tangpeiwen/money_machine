from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from .asset import AssetInDB

# 基础资产模型
class AssetBase(BaseModel):
    name: str = Field(..., description="资产名称")
    symbol: str = Field(..., description="资产代号")
    chain: Optional[str] = Field(None, description="区块链网络")
    token_address: Optional[str] = Field(None, description="代币地址")
    asset_type: str = Field(default="cryptocurrency", description="资产类型")
    storage: Optional[str] = Field(None, description="存储位置")


# 创建资产请求
class AssetCreate(AssetBase):
    tokens_holding: float = Field(..., ge=0, description="持有数量")


# 更新资产请求
class AssetUpdate(BaseModel):
    tokens_holding: Optional[float] = Field(None, ge=0, description="持有数量")
    storage: Optional[str] = Field(None, description="存储位置")


# 完整资产响应
class AssetResponse(AssetBase):
    current_price: float = Field(default=0.0, description="当前价格")
    tokens_holding: float = Field(default=0.0, description="持有数量")
    holding_value: float = Field(default=0.0, description="持仓价值")

    class Config:
        from_attributes = True


# 投资组合响应
class PortfolioResponse(BaseModel):
    user_id: str
    assets: List[dict]  # 确保包含 name, symbol, amount, value, dailyChange
    total_value: float
    last_updated: datetime | None = None

    class Config:
        from_attributes = True
