from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class User(BaseModel):
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    hashed_password: str = Field(..., description="加密后的密码")
    is_active: bool = Field(default=True, description="是否激活")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    last_login: Optional[datetime] = Field(default=None, description="最后登录时间")
    settings: dict = Field(default_factory=dict, description="用户设置")
