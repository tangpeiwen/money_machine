# app/config.py
import os
from dotenv import load_dotenv

# 仅在本地开发环境使用 dotenv
if os.getenv('ENVIRONMENT') != 'production':
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

class Settings:
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    NOTION_HISTORY_DATABASE_ID = os.getenv('NOTION_HISTORY_DATABASE_ID')
    CMC_API_KEY = os.getenv('CMC_API_KEY')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    def __init__(self):
        # 验证必要的环境变量
        required_vars = ['NOTION_TOKEN', 'NOTION_DATABASE_ID', 'NOTION_HISTORY_DATABASE_ID']
        missing_vars = [var for var in required_vars if not getattr(self, var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

settings = Settings()