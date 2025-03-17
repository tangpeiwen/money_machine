from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from .api.v1.api import api_router

app = FastAPI()


# 创建一个中间件来处理 HTTPS
class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 检查 X-Forwarded-Proto 头，这通常由代理服务器设置
        forwarded_proto = request.headers.get("X-Forwarded-Proto")

        # 如果请求是通过 HTTP 而不是 HTTPS 发送的
        if forwarded_proto == "http":
            # 构建新的 HTTPS URL
            url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(url), status_code=301)

        return await call_next(request)


# 添加 HTTPS 重定向中间件


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 前端URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(HTTPSRedirectMiddleware)

app.include_router(api_router, prefix="/api/v1")
