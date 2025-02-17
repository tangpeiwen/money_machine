from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TradeType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Trade(BaseModel):
    user_id: str = Field(..., description="用户ID")
    coin: str = Field(..., description="币种")
    amount: float = Field(..., description="数量")
    price: float = Field(..., description="价格")
    type: TradeType = Field(..., description="交易类型")
    total: float = Field(..., description="总金额")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="交易时间")
    notes: str = Field(default="", description="备注")
