from typing import Optional
from datetime import datetime
from uuid import UUID


class Cryptocurrency:
    """加密货币基本信息模型"""

    id: UUID
    symbol: str
    name: str
    logo_url: Optional[str]
    created_at: datetime
    updated_at: datetime
