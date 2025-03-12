from binance.client import Client
from typing import List, Dict, Optional
import logging
from datetime import datetime
from .asset import AssetService
from .history import HistoryService
from ..core.database import db

from ..core.config import settings
import okx.Account as Account
import okx.MarketData as Market  # 改用 Market API
from pybitget import Client as BitgetClient  # 修改导入
from ..core.utils import get_crypto_logo

logger = logging.getLogger(__name__)


class ExchangeService:
    # 设置最小持仓价值（比如 1 USDT）
    MIN_HOLDING_VALUE = 1.0

    @staticmethod
    async def sync_binance_assets(user_id: str, api_key: str, api_secret: str) -> List[Dict]:
        """同步 Binance 账户资产到数据库"""
        try:
            # 初始化 Binance 客户端
            client = Client(api_key, api_secret, tld="com")

            # 获取账户快照
            spot = client.get_account_snapshot(type="SPOT")
            if not spot.get("snapshotVos"):
                raise Exception("No snapshot data available")

            # 获取最新的快照数据
            latest_snapshot = spot["snapshotVos"][-1]
            balances = latest_snapshot["data"]["balances"]

            # 获取所有交易对的价格
            tickers = client.get_all_tickers()
            price_dict = {ticker["symbol"]: float(ticker["price"]) for ticker in tickers}

            # 过滤出余额大于 0 的资产
            assets = [balance for balance in balances if float(balance["free"]) > 0 or float(balance["locked"]) > 0]

            supabase = db.get_supabase_client()
            updated_assets = []

            for asset in assets:
                symbol = asset["asset"]
                total_amount = float(asset["free"]) + float(asset["locked"])

                try:
                    # 获取价格和24小时变化
                    usdt_pair = f"{symbol}USDT"

                    if symbol == "USDT":
                        current_price = 1.0
                        percent_change_24h = 0.0
                    else:
                        # 从价格字典中获取价格
                        current_price = price_dict.get(usdt_pair, 0.0)

                        # 获取24小时价格变化
                        try:
                            ticker_24h = client.get_ticker(symbol=usdt_pair)
                            percent_change_24h = float(ticker_24h["priceChangePercent"])
                        except:
                            percent_change_24h = 0.0

                    holding_value = total_amount * current_price

                    # 跳过持仓价值小于最小值的资产
                    if holding_value < ExchangeService.MIN_HOLDING_VALUE:
                        logger.info(f"Skipping {symbol} due to small holding value: {holding_value} USDT")
                        continue

                    # 准备资产数据
                    asset_data = {
                        "user_id": user_id,
                        "symbol": symbol,
                        "name": symbol,  # 可以后续添加获取完整名称的逻辑
                        "tokens_holding": total_amount,
                        "current_price": current_price,
                        "holding_value": holding_value,
                        "percent_change_24h": percent_change_24h,
                        "storage": "Binance",
                        "asset_type": "cryptocurrency",
                        "logo_url": await get_crypto_logo(symbol),
                        "updated_at": datetime.utcnow().isoformat(),
                    }

                    logger.info(f"Updating asset: {symbol}, Amount: {total_amount}, Price: {current_price}")

                    # 使用 upsert 操作更新数据库
                    result = supabase.table("assets").upsert(asset_data, on_conflict="user_id,symbol,storage").execute()

                    if result.data:
                        updated_assets.append(result.data[0])
                        logger.info(f"Successfully updated {symbol}")

                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
                    continue

            # 创建历史记录
            await HistoryService.record_portfolio_snapshot(user_id)

            return updated_assets

        except Exception as e:
            logger.error(f"Error syncing Binance assets: {str(e)}")
            raise Exception(f"Failed to sync Binance assets: {str(e)}")

    @staticmethod
    async def sync_okx_assets(user_id: str, api_key: str, api_secret: str, passphrase: str) -> List[Dict]:
        """同步 OKX 账户资产到数据库"""
        try:
            # 初始化 OKX API
            flag = "0"  # 实盘
            account_api = Account.AccountAPI(api_key, api_secret, passphrase, False, flag)
            market_api = Market.MarketAPI(api_key, api_secret, passphrase, False, flag)

            # 获取账户余额
            balance = account_api.get_account_balance()
            if not balance.get("data"):
                raise Exception("No balance data available")

            supabase = db.get_supabase_client()
            updated_assets = []

            # 处理每个资产
            for asset in balance["data"][0].get("details", []):
                try:
                    symbol = asset["ccy"]
                    total_amount = float(asset.get("availBal", 0))
                    holding_value = float(asset.get("eqUsd", 0))

                    # 跳过持仓价值小于最小值的资产
                    if holding_value < ExchangeService.MIN_HOLDING_VALUE:
                        logger.info(f"Skipping {symbol} due to small holding value: {holding_value} USDT")
                        continue

                    # 获取当前价格和24小时变化
                    if symbol == "USDT":
                        current_price = 1.0
                        percent_change_24h = 0.0
                    else:
                        try:
                            # 获取ticker数据
                            ticker_data = market_api.get_ticker(instId=f"{symbol}-USDT")
                            if ticker_data.get("data") and ticker_data["code"] == "0":
                                ticker = ticker_data["data"][0]
                                current_price = float(ticker["last"])
                                # 计算24小时价格变化
                                open_24h = float(ticker["open24h"])
                                percent_change_24h = (
                                    ((current_price - open_24h) / open_24h * 100) if open_24h > 0 else 0.0
                                )
                            else:
                                logger.warning(f"No ticker data for {symbol}")
                                current_price = 0.0
                                percent_change_24h = 0.0
                        except Exception as e:
                            logger.error(f"Error getting ticker for {symbol}: {str(e)}")
                            current_price = 0.0
                            percent_change_24h = 0.0

                    # 准备资产数据
                    asset_data = {
                        "user_id": user_id,
                        "symbol": symbol,
                        "name": symbol,
                        "tokens_holding": total_amount,
                        "current_price": current_price,
                        "holding_value": holding_value,
                        "percent_change_24h": percent_change_24h,
                        "storage": "OKX",
                        "asset_type": "cryptocurrency",
                        "logo_url": await get_crypto_logo(symbol),
                        "updated_at": datetime.utcnow().isoformat(),
                    }

                    logger.info(
                        f"Updating OKX asset: {symbol}, Amount: {total_amount}, Value: {holding_value} USD, Change: {percent_change_24h}%"
                    )

                    # 更新数据库
                    result = supabase.table("assets").upsert(asset_data, on_conflict="user_id,symbol,storage").execute()

                    if result.data:
                        updated_assets.append(result.data[0])
                        logger.info(f"Successfully updated {symbol}")

                except Exception as e:
                    logger.error(f"Error processing OKX asset {symbol}: {str(e)}")
                    continue

            # 创建历史记录
            await HistoryService.record_portfolio_snapshot(user_id)

            return updated_assets

        except Exception as e:
            logger.error(f"Error syncing OKX assets: {str(e)}")
            raise Exception(f"Failed to sync OKX assets: {str(e)}")

    @staticmethod
    async def sync_bitget_assets(user_id: str, api_key: str, api_secret: str, passphrase: str) -> List[Dict]:
        """同步 Bitget 账户资产到数据库"""
        try:
            # 初始化 Bitget API
            client = BitgetClient(api_key, api_secret, passphrase)

            # 获取账户余额
            balance = client.spot_get_account_assets()
            if not balance or not balance.get("data"):
                raise Exception("Failed to get balance data")

            # 获取所有交易对的ticker数据
            tickers = client.spot_get_tickers()
            if not tickers or not tickers.get("data"):
                raise Exception("Failed to get ticker data")

            # 创建价格和24h变化字典
            price_data = {}
            for ticker in tickers.get("data", []):
                symbol = ticker["symbol"].replace("USDT", "")  # 移除USDT后缀
                price_data[symbol] = {
                    "price": float(ticker["buyOne"]),  # 使用 buyOne 作为当前价格
                    "change_24h": float(ticker["change"]) * 100,  # 转换为百分比
                }

            supabase = db.get_supabase_client()
            updated_assets = []

            # 处理每个资产
            for asset in balance.get("data", []):
                try:
                    symbol = asset["coinName"]
                    # 计算总余额 = 可用 + 冻结 + 锁定
                    total_amount = (
                        float(asset.get("available", 0)) + float(asset.get("frozen", 0)) + float(asset.get("lock", 0))
                    )

                    # 跳过零余额资产
                    if total_amount <= 0:
                        continue

                    # 获取价格和24h变化
                    if symbol == "USDT":
                        current_price = 1.0
                        percent_change_24h = 0.0
                        holding_value = total_amount
                    else:
                        if symbol not in price_data:
                            logger.warning(f"No price data for {symbol}")
                            continue

                        current_price = price_data[symbol]["price"]
                        percent_change_24h = price_data[symbol]["change_24h"]
                        holding_value = total_amount * current_price

                    # 跳过小额资产
                    if holding_value < ExchangeService.MIN_HOLDING_VALUE:
                        logger.info(f"Skipping {symbol} due to small holding value: {holding_value} USDT")
                        continue

                    # 准备资产数据
                    asset_data = {
                        "user_id": user_id,
                        "symbol": symbol,
                        "name": symbol,
                        "tokens_holding": total_amount,
                        "current_price": current_price,
                        "holding_value": holding_value,
                        "percent_change_24h": percent_change_24h,
                        "storage": "Bitget",
                        "asset_type": "cryptocurrency",
                        "logo_url": await get_crypto_logo(symbol),
                        "updated_at": datetime.utcnow().isoformat(),
                    }

                    logger.info(f"Updating Bitget asset: {symbol}, Amount: {total_amount}, Value: {holding_value} USD")

                    # 更新数据库
                    result = supabase.table("assets").upsert(asset_data, on_conflict="user_id,symbol,storage").execute()

                    if result.data:
                        updated_assets.append(result.data[0])
                        logger.info(f"Successfully updated {symbol}")

                except Exception as e:
                    logger.error(f"Error processing Bitget asset {symbol}: {str(e)}")
                    continue

            # 创建历史记录
            await HistoryService.record_portfolio_snapshot(user_id)

            return updated_assets

        except Exception as e:
            logger.error(f"Error syncing Bitget assets: {str(e)}")
            raise Exception(f"Failed to sync Bitget assets: {str(e)}")

    @staticmethod
    async def get_user_connections(user_id: str) -> List[Dict]:
        """Get all exchange connections for a user"""
        try:
            supabase = db.get_supabase_client()
            result = supabase.table("exchange_connections").select("*").eq("user_id", user_id).execute()

            return result.data
        except Exception as e:
            logger.error(f"Error getting user connections: {str(e)}")
            raise Exception(f"Failed to get exchange connections: {str(e)}")

    @staticmethod
    async def create_connection(
        user_id: str,
        exchange: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
    ) -> Dict:
        """Create a new exchange connection"""
        try:
            # In a real app, you would encrypt these credentials
            # For now, we'll just store the exchange name
            supabase = db.get_supabase_client()

            connection_data = {
                "user_id": user_id,
                "exchange": exchange,
                "is_active": True,
                # Don't store actual API keys in the database for this demo
                # In a real app, you would encrypt these
                "has_credentials": bool(api_key and api_secret),
            }

            result = (
                supabase.table("exchange_connections").upsert(connection_data, on_conflict="user_id,exchange").execute()
            )

            if not result.data:
                raise Exception("Failed to create connection")

            # Sync assets immediately if possible
            if exchange.lower() == "binance":
                await ExchangeService.sync_binance_assets(
                    user_id=user_id,
                    api_key=api_key or settings.BINANCE_API_KEY,
                    api_secret=api_secret or settings.BINANCE_API_SECRET,
                )
            elif exchange.lower() == "okx":
                await ExchangeService.sync_okx_assets(
                    user_id=user_id,
                    api_key=api_key or settings.OKX_API_KEY,
                    api_secret=api_secret or settings.OKX_API_SECRET,
                    passphrase=passphrase or settings.OKX_PASSPHRASE,
                )
            elif exchange.lower() == "bitget":
                await ExchangeService.sync_bitget_assets(
                    user_id=user_id,
                    api_key=api_key or settings.BITGET_API_KEY,
                    api_secret=api_secret or settings.BITGET_API_SECRET,
                    passphrase=passphrase or settings.BITGET_PASSPHRASE,
                )

            return result.data[0]
        except Exception as e:
            logger.error(f"Error creating connection: {str(e)}")
            raise Exception(f"Failed to create exchange connection: {str(e)}")

    @staticmethod
    async def delete_connection(user_id: str, connection_id: str) -> bool:
        """Delete an exchange connection"""
        try:
            supabase = db.get_supabase_client()

            # First, get the connection to find the exchange
            connection = (
                supabase.table("exchange_connections")
                .select("*")
                .eq("id", connection_id)
                .eq("user_id", user_id)
                .execute()
            )

            if not connection.data:
                return False

            # Delete the connection
            result = (
                supabase.table("exchange_connections").delete().eq("id", connection_id).eq("user_id", user_id).execute()
            )

            # Delete associated assets
            exchange = connection.data[0]["exchange"]
            (supabase.table("assets").delete().eq("user_id", user_id).eq("storage", exchange).execute())

            return True
        except Exception as e:
            logger.error(f"Error deleting connection: {str(e)}")
            raise Exception(f"Failed to delete exchange connection: {str(e)}")
