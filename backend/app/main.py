# Creates the FastAPI application instance
# Adds CORS middleware to allow cross-origin requests
# Includes the API router with a prefix of /api/v1

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.api import api_router

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 前端URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router, prefix="/api/v1")
