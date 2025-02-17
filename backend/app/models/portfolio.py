from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Asset(BaseModel):
    name: str = Field(..., description="资产名称")
    symbol: str = Field(..., description="资产代号")
    chain: Optional[str] = Field(None, description="区块链网络")
    token_address: Optional[str] = Field(None, description="代币地址")
    asset_type: str = Field(default="cryptocurrency", description="资产类型")
    storage: Optional[str] = Field(None, description="存储位置")
    current_price: float = Field(default=0.0, description="当前价格")
    tokens_holding: float = Field(default=0.0, description="持有数量")
    holding_value: float = Field(default=0.0, description="持仓价值")


class Portfolio(BaseModel):
    user_id: str = Field(..., description="用户ID")
    assets: List[Asset] = Field(default_factory=list, description="资产列表")
    total_value: float = Field(default=0.0, description="总价值")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="最后更新时间")
