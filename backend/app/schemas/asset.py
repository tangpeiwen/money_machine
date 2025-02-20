from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AssetBase(BaseModel):
    symbol: str = Field(..., description="资产代号")
    chain: Optional[str] = Field(None, description="区块链网络")
    token_address: Optional[str] = Field(None, description="代币地址")
    asset_type: str = Field(default="cryptocurrency", description="资产类型")
    storage: Optional[str] = Field(None, description="存储位置")


class AssetCreate(BaseModel):
    symbol: str = Field(..., description="资产代号")
    storage: Optional[str] = Field(None, description="存储位置")
    tokens_holding: float = Field(..., ge=0, description="持有数量")


class AssetUpdate(BaseModel):
    symbol: str = Field(..., description="资产代号")
    tokens_holding: Optional[float] = Field(None, ge=0, description="持有数量")
    storage: Optional[str] = Field(None, description="存储位置")


class AssetInDB(AssetBase):
    id: str
    user_id: str
    name: str = Field(..., description="资产名称")
    current_price: float = Field(default=0.0)
    tokens_holding: float = Field(default=0.0)
    holding_value: float = Field(default=0.0)
    percent_change_24h: float = Field(default=0.0, description="24小时价格变化百分比")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetResponse(AssetInDB):
    pass
