from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Settings(BaseSettings):
    # 基础配置
    APP_NAME: str = "Crypto Portfolio"
    API_V1_STR: str = "/api/v1"

    # Supabase配置
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # JWT配置
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时

    # 外部API配置
    CMC_API_KEY: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
