from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class ConnectionRequest(BaseModel):
    exchange: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None


class ExchangeConnection(BaseModel):
    id: str
    user_id: str
    exchange: str
    is_active: bool
    has_credentials: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
