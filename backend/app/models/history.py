from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PortfolioHistory(BaseModel):
    user_id: str = Field(..., description="用户ID")
    symbol: str = Field(..., description="资产代号")
    asset_type: str = Field(default="cryptocurrency", description="资产类型")
    current_price: float = Field(default=0.0, description="当前价格")
    tokens_holding: float = Field(default=0.0, description="持有数量")
    holding_value: float = Field(default=0.0, description="持仓价值")
    date: datetime = Field(default_factory=datetime.utcnow, description="记录时间")
