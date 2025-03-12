from fastapi import APIRouter, HTTPException
from ....services.exchange import ExchangeService
from ....core.utils import TEMP_USER_ID
from ....core.config import settings
from ....schemas.exchange import ConnectionRequest, ExchangeConnection
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/binance/sync")
async def sync_binance_assets(user_id: str = TEMP_USER_ID):
    """同步 Binance 账户资产"""
    try:
        if not settings.BINANCE_API_KEY or not settings.BINANCE_API_SECRET:
            raise HTTPException(status_code=400, detail="Binance API credentials not configured in environment")

        assets = await ExchangeService.sync_binance_assets(
            user_id=user_id, api_key=settings.BINANCE_API_KEY, api_secret=settings.BINANCE_API_SECRET
        )
        return {"message": "Successfully synced Binance assets", "assets": assets}
    except Exception as e:
        logger.error(f"Error in sync_binance_assets: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/okx/sync")
async def sync_okx_assets(user_id: str = TEMP_USER_ID):
    """同步 OKX 账户资产"""
    try:
        if not all([settings.OKX_API_KEY, settings.OKX_API_SECRET, settings.OKX_PASSPHRASE]):
            raise HTTPException(status_code=400, detail="OKX API credentials not configured in environment")

        assets = await ExchangeService.sync_okx_assets(
            user_id=user_id,
            api_key=settings.OKX_API_KEY,
            api_secret=settings.OKX_API_SECRET,
            passphrase=settings.OKX_PASSPHRASE,
        )
        return {"message": "Successfully synced OKX assets", "assets": assets}
    except Exception as e:
        logger.error(f"Error in sync_okx_assets: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bitget/sync")
async def sync_bitget_assets(user_id: str = TEMP_USER_ID):
    """同步 Bitget 账户资产"""
    try:
        if not all([settings.BITGET_API_KEY, settings.BITGET_API_SECRET, settings.BITGET_PASSPHRASE]):
            raise HTTPException(status_code=400, detail="Bitget API credentials not configured in environment")

        assets = await ExchangeService.sync_bitget_assets(
            user_id=user_id,
            api_key=settings.BITGET_API_KEY,
            api_secret=settings.BITGET_API_SECRET,
            passphrase=settings.BITGET_PASSPHRASE,
        )
        return {"message": "Successfully synced Bitget assets", "assets": assets}
    except Exception as e:
        logger.error(f"Error in sync_bitget_assets: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connections")
async def get_connections(user_id: str = TEMP_USER_ID):
    """Get all exchange connections for the user"""
    try:
        connections = await ExchangeService.get_user_connections(user_id)
        return connections
    except Exception as e:
        logger.error(f"Error getting connections: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/connections", response_model=ExchangeConnection)
async def create_connection(request: ConnectionRequest, user_id: str = TEMP_USER_ID):
    """Create a new exchange connection"""
    try:
        connection = await ExchangeService.create_connection(
            user_id=user_id,
            exchange=request.exchange,
            api_key=request.api_key,
            api_secret=request.api_secret,
            passphrase=request.passphrase,
        )
        return connection
    except Exception as e:
        logger.error(f"Error creating connection: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str, user_id: str = TEMP_USER_ID):
    """Delete an exchange connection"""
    try:
        success = await ExchangeService.delete_connection(user_id, connection_id)
        if not success:
            raise HTTPException(status_code=404, detail="Connection not found")
        return {"message": "Connection deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting connection: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
