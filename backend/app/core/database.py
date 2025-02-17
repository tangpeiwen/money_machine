from supabase import create_client, Client
from .config import settings


class Database:
    supabase_client: Client = None

    async def connect_to_database(self):
        """初始化数据库连接"""
        self.init_supabase_client()

    async def close_database_connection(self):
        """关闭数据库连接"""
        pass  # Supabase client 不需要显式关闭

    def init_supabase_client(self):
        """初始化 Supabase 客户端"""
        if not self.supabase_client:
            self.supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return self.supabase_client

    def get_supabase_client(self) -> Client:
        """获取 Supabase 客户端"""
        if not self.supabase_client:
            self.init_supabase_client()
        return self.supabase_client


db = Database()
