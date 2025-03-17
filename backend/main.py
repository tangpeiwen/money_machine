from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import db
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时连接数据库
    await db.connect_to_database()
    yield
    # 关闭时断开连接
    await db.close_database_connection()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# 配置CORS

origins = [
    "http://localhost:3000",  # Your local frontend
    " https://moneymachine-production.up.railway.app",  # Your production frontend domain
    # Add any other domains that need access
]
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"],
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(HTTPSRedirectMiddleware)


# 注册 API 路由
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
