from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Query

from ....services.cryptocurrency import CryptocurrencyService
from ....schemas.cryptocurrency import CryptocurrencyResponse, CryptocurrencyCreate, CryptocurrencyUpdate

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search", response_model=List[CryptocurrencyResponse])
async def search_cryptocurrencies(
    query: str = Query(..., description="搜索关键词"), limit: int = Query(10, description="返回结果数量限制")
):
    """搜索加密货币"""
    try:
        results = await CryptocurrencyService.search_cryptocurrency(query, limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search cryptocurrencies: {str(e)}")


@router.get("/top", response_model=List[CryptocurrencyResponse])
async def get_top_cryptocurrencies(limit: int = Query(100, description="返回结果数量限制")):
    """获取排名靠前的加密货币"""
    try:
        results = await CryptocurrencyService.get_top_cryptocurrencies(limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get top cryptocurrencies: {str(e)}")


@router.post("", response_model=CryptocurrencyResponse)
async def create_cryptocurrency(crypto: CryptocurrencyCreate):
    """创建新的加密货币记录"""
    try:
        # 检查是否已存在
        existing = await CryptocurrencyService.get_cryptocurrency(crypto.symbol)
        if existing:
            raise HTTPException(status_code=400, detail=f"Cryptocurrency with symbol {crypto.symbol} already exists")

        # 创建新记录
        result = await CryptocurrencyService.create_cryptocurrency(crypto)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create cryptocurrency: {str(e)}")


@router.put("/{symbol}", response_model=CryptocurrencyResponse)
async def update_cryptocurrency(symbol: str, crypto_update: CryptocurrencyUpdate):
    """更新加密货币信息"""
    try:
        # 检查是否存在
        existing = await CryptocurrencyService.get_cryptocurrency(symbol)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Cryptocurrency with symbol {symbol} not found")

        # 更新记录
        result = await CryptocurrencyService.update_cryptocurrency(symbol, crypto_update)
        if not result:
            raise HTTPException(status_code=500, detail=f"Failed to update cryptocurrency {symbol}")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update cryptocurrency: {str(e)}")


@router.get("/{symbol}", response_model=CryptocurrencyResponse)
async def get_cryptocurrency(symbol: str):
    """获取加密货币信息"""
    try:
        crypto = await CryptocurrencyService.get_cryptocurrency(symbol)
        if not crypto:
            raise HTTPException(status_code=404, detail=f"Cryptocurrency with symbol {symbol} not found")
        return crypto
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cryptocurrency: {str(e)}")
