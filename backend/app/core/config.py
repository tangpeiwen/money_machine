from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Settings(BaseSettings):
    # 基础配置
    APP_NAME: str = "Crypto Portfolio"
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Money Machine"

    # Supabase配置
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # 外部API配置
    CMC_API_KEY: str
    COINAPI_API_KEY: str  # CoinAPI 密钥，从 .env 加载
    BINANCE_API_KEY: str
    BINANCE_API_SECRET: str

    # OKX API 配置
    OKX_API_KEY: str
    OKX_API_SECRET: str
    OKX_PASSPHRASE: str

    # Bitget API 配置
    BITGET_API_KEY: str = ""
    BITGET_API_SECRET: str = ""
    BITGET_PASSPHRASE: str = ""

    # CoinGecko API settings
    COINGECKO_API_URL: str = "https://api.coingecko.com/api/v3"

    # ARK API 配置
    ARK_API_KEY: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略 .env 文件中的额外字段


settings = Settings()
