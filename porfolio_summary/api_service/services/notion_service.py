from datetime import datetime, timedelta
from collections import defaultdict
import json

from notion_client import Client

from api_service.config import settings
from api_service.utils.logger import logger
from api_service.services.crypto_service import CryptoService
from api_service.services.dex_service import DexService


class NotionService:
    def __init__(self):
        self.client = Client(auth=settings.NOTION_TOKEN)
        self.crypto_service = CryptoService()
        self.dex_service = DexService()

    async def update_portfolio_prices(self):
        """更新主表中的所有资产价格并返回汇总数据"""
        try:
            query = self.client.databases.query(database_id=settings.NOTION_DATABASE_ID)

            crypto_summary = {}
            asset_types = {}

            for page in query["results"]:
                asset_type = page["properties"].get("资产类型", {}).get("select", {}).get("name", "")
                logger.info(f"资产类型: {asset_type}")

                result = None
                if asset_type == "cryptocurrency":
                    result = await self._process_portfolio_item(page)
                elif asset_type == "altcoin":
                    result = await self._process_altcoin_item(page)
                logger.info(f"result: {result}")

                if result:
                    # 合并汇总数据
                    for symbol, data in result["summary"].items():
                        logger.info(f"symbol: {symbol}, data: {data}")
                        if symbol not in crypto_summary:
                            crypto_summary[symbol] = data
                        else:
                            crypto_summary[symbol]["total_tokens"] += data["total_tokens"]
                            crypto_summary[symbol]["total_value"] += data["total_value"]
                    asset_types.update(result["asset_types"])

            # logger.info(f"最终汇总数据: {crypto_summary}")
            # logger.info(f"资产类型: {asset_types}")
            return crypto_summary, asset_types

        except Exception as e:
            logger.error(f"更新投资组合价格时出错: {e}")
            raise

    async def _process_portfolio_item(self, page) -> dict:
        """处理单个投资组合项目（用于汇总）"""
        try:
            properties = page["properties"]
            asset_type = properties.get("资产类型", {}).get("select", {}).get("name", "")
            tokens_holding = float(properties.get("Tokens Holding", {}).get("number", 0))

            # 根据资产类型获取价格数据
            if asset_type == "cryptocurrency":
                name, symbol = self._extract_name_symbol(properties)
                price_data = await self._get_crypto_data(name, symbol)
                if not price_data["success"]:
                    return None
                token_info = {"name": price_data["name"], "symbol": price_data["symbol"], "price": price_data["price"]}
            elif asset_type == "altcoin":
                chain = properties.get("Chain", {}).get("select", {}).get("name", "")
                token_address = (
                    properties.get("Token Address", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
                )
                if not chain or not token_address:
                    return None
                token_info = self.dex_service.get_token_info(chain, token_address)
                if token_info is None:
                    return None
            else:
                return None

            # 更新 Notion 页面
            await self._update_notion_page(page["id"], token_info)

            # 准备汇总数据
            symbol = token_info["symbol"].upper()
            current_price = token_info["price"]
            total_value = tokens_holding * current_price

            logger.info(
                f"准备的汇总数据 - Symbol: {symbol}, Price: {current_price}, "
                f"Tokens: {tokens_holding}, Total Value: {total_value}"
            )

            # 返回需要汇总的数据
            return {
                "summary": {
                    symbol: {
                        "name": token_info["name"],
                        "symbol": symbol,
                        "current_price": current_price,
                        "total_tokens": tokens_holding,
                        "total_value": total_value,
                    }
                },
                "asset_types": {symbol: asset_type},
            }

        except Exception as e:
            logger.error(f"处理投资组合项目时出错: {e}")
            logger.exception(e)
            return None

    def _extract_asset_type(self, properties):
        """从属性中提取资产类型"""
        return properties.get("资产类型", {}).get("select", {}).get("name", "cryptocurrency")

    def _extract_name_symbol(self, properties):
        """从属性中提取名称和符号"""
        name = ""
        symbol = ""

        name_data = properties.get("Name", {}).get("title", [])
        if name_data and name_data[0].get("text"):
            name = name_data[0]["text"].get("content", "").strip()

        symbol_data = properties.get("Symbol", {}).get("rich_text", [])
        if symbol_data and symbol_data[0].get("text"):
            symbol = symbol_data[0]["text"].get("content", "").strip()

        return name, symbol

    async def _get_crypto_data(self, name, symbol):
        """获取加密货币数据，尝试多种搜索方式"""
        crypto_data = {"success": False}

        if symbol:
            crypto_data = self.crypto_service.get_crypto_price(symbol, "symbol")

        if not crypto_data["success"] and name:
            crypto_data = self.crypto_service.get_crypto_price(name, "slug")

        if not crypto_data["success"] and name:
            crypto_data = self.crypto_service.get_crypto_price(name, "symbol")

        return crypto_data

    async def clear_today_history(self, today):
        """清除今天的历史记录"""
        try:
            existing_records = self.client.databases.query(
                database_id=settings.NOTION_HISTORY_DATABASE_ID, filter={"property": "Date", "date": {"equals": today}}
            )

            for record in existing_records["results"]:
                self.client.pages.update(page_id=record["id"], archived=True)

            if existing_records["results"]:
                logger.info(f"已删除 {len(existing_records['results'])} 条当天的历史记录")

        except Exception as e:
            logger.error(f"删除当天历史记录时出错: {e}")

    async def save_portfolio_history(self, crypto_summary, asset_types, today):
        """保存投资组合历史记录"""
        updated_count = 0
        logger.info(f"crypto_summary: {crypto_summary}")
        for search_key, data in crypto_summary.items():
            if data["total_value"] > 0:
                try:
                    # 使用对应的资产类型
                    asset_type = asset_types.get(search_key, "cryptocurrency")

                    self.client.pages.create(
                        parent={"database_id": settings.NOTION_HISTORY_DATABASE_ID},
                        properties={
                            "Date": {"date": {"start": today}},
                            "Symbol": {"rich_text": [{"text": {"content": data["symbol"]}}]},
                            "资产类型": {"select": {"name": asset_type}},
                            "Current Price": {"number": round(data["current_price"], 8)},
                            "Tokens Holding": {"number": round(data["total_tokens"], 4)},
                        },
                    )

                    updated_count += 1
                    logger.info(
                        f"成功保存 {search_key} 的汇总数据: "
                        f"总持仓: {data['total_tokens']:.8f}, "
                        f"总价值: ${data['total_value']:.2f}, "
                    )

                except Exception as e:
                    logger.error(f"保存 {search_key} 的汇总数据时出错: {e}")
                    continue

        return updated_count

    async def get_portfolio_summary(self) -> dict:
        """获取投资组合数据摘要"""
        try:
            # 获取当前数据和总值
            current_data = await self._get_current_portfolio_values()

            # 获取昨日数据和变化
            yesterday_data = await self._get_yesterday_portfolio_data()

            # 计算变化
            changes = self._calculate_portfolio_changes(
                current_data["total"], yesterday_data["total"] if yesterday_data else 0
            )

            # 准备摘要数据
            summary_data = {
                "total_value": round(current_data["total"], 2),
                "has_previous_data": bool(yesterday_data),
                "change_amount": round(changes["amount"], 2) if changes["amount"] is not None else None,
                "change_percentage": round(changes["percentage"], 3) if changes["percentage"] is not None else None,
                "date": datetime.now().strftime("%Y-%m-%d"),
            }

            logger.info(f"生成投资组合摘要: {summary_data}")
            return summary_data

        except Exception as e:
            logger.error(f"获取投资组合摘要时出错: {e}")
            raise

    async def _get_current_portfolio_values(self) -> dict:
        """获取当前投资组合的值"""
        try:
            query = self.client.databases.query(
                database_id=settings.NOTION_DATABASE_ID,
            )

            portfolio_data = defaultdict(float)
            current_total = 0

            for page in query["results"]:
                properties = page["properties"]
                symbol = (
                    properties.get("Symbol", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "Unknown")
                )
                holding_value = float(properties.get("Holding Values", {}).get("formula", {}).get("number", 0))

                if holding_value:
                    portfolio_data[symbol] += holding_value
                    current_total += holding_value

            return {"total": current_total, "holdings": dict(portfolio_data)}

        except Exception as e:
            logger.error(f"获取当前投资组合值时出错: {e}")
            raise

    async def _get_yesterday_portfolio_data(self) -> dict:
        """获取昨日投资组合数据"""
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            query = self.client.databases.query(
                database_id=settings.NOTION_HISTORY_DATABASE_ID,
                filter={"property": "Date", "date": {"equals": yesterday}},
            )

            if not query["results"]:
                return None

            # 构建持仓数据字典
            holdings = {}
            yesterday_total = 0

            for page in query["results"]:
                properties = page["properties"]
                symbol = properties.get("Symbol", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
                holding_value = float(properties.get("Holding Values", {}).get("formula", {}).get("number", 0))

                if symbol and holding_value:
                    holdings[symbol] = holding_value
                    yesterday_total += holding_value

            logger.info(f"昨日数据 - 总值: {yesterday_total}, 持仓: {holdings}")

            return {"total": yesterday_total, "holdings": holdings}

        except Exception as e:
            logger.error(f"获取昨日投资组合数据时出错: {e}")
            logger.exception(e)  # 添加详细的错误日志
            raise

    def _calculate_portfolio_changes(self, current_total: float, yesterday_total: float) -> dict:
        """计算投资组合的变化"""
        if not yesterday_total:
            return {"amount": None, "percentage": None}

        change_amount = current_total - yesterday_total
        change_percentage = (change_amount / yesterday_total * 100) if yesterday_total else 0

        return {"amount": change_amount, "percentage": change_percentage}

    async def _update_notion_page(self, page_id, crypto_data):
        """更新 Notion 页面的加密货币数据"""
        try:
            update_properties = {
                "Current Price": {"number": crypto_data["price"]},
                "Symbol": {"rich_text": [{"text": {"content": crypto_data["symbol"]}}]},
                "Name": {"title": [{"text": {"content": crypto_data["name"]}}]},
            }

            self.client.pages.update(page_id=page_id, properties=update_properties)

            logger.info(f"更新主表 - {crypto_data['name']}({crypto_data['symbol']}), " f"价格: ${crypto_data['price']}")

        except Exception as e:
            logger.error(f"更新 Notion 页面时出错: {e}")
            raise

    async def update_single_price(self, page_id: str) -> dict:
        """更新单个资产的价格数据"""
        try:
            # 获取页面数据
            page = self.client.pages.retrieve(page_id=page_id)
            properties = page["properties"]
            asset_type = properties.get("资产类型", {}).get("select", {}).get("name", "")

            # 根据资产类型获取价格数据
            if asset_type == "cryptocurrency":
                name, symbol = self._extract_name_symbol(properties)
                price_data = await self._get_crypto_data(name, symbol)
                if not price_data["success"]:
                    raise Exception(f"无法获取 {name}({symbol}) 的价格数据")
                token_info = {"name": price_data["name"], "symbol": price_data["symbol"], "price": price_data["price"]}
            elif asset_type == "altcoin":
                chain = properties.get("Chain", {}).get("select", {}).get("name", "")
                token_address = (
                    properties.get("Token Address", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
                )
                if not chain or not token_address:
                    raise Exception(f"Altcoin 记录缺少必要信息 - Chain: {chain}, Address: {token_address}")
                token_info = self.dex_service.get_token_info(chain, token_address)
                if token_info is None:
                    raise Exception(f"无法获取代币信息 - Chain: {chain}, Address: {token_address}")
            else:
                raise Exception(f"不支持的资产类型: {asset_type}")

            # 更新 Notion 页面
            await self._update_notion_page(page_id, token_info)

            logger.info(
                f"更新价格成功 - Name: {token_info['name']}, "
                f"Symbol: {token_info['symbol']}, Price: ${token_info['price']}"
            )

            return {"status": "success", "data": token_info}

        except Exception as e:
            logger.error(f"更新单个资产价格时出错: {e}")
            logger.exception(e)
            raise

    async def _process_altcoin_item(self, page) -> dict:
        """处理单个 Altcoin 资产项目（用于汇总）"""
        try:
            properties = page["properties"]

            # 获取必要的信息
            chain = properties.get("Chain", {}).get("select", {}).get("name", "")
            token_address = (
                properties.get("Token Address", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            )
            tokens_holding = float(properties.get("Tokens Holding", {}).get("number", 0))  # 确保转换为 float

            if not chain or not token_address:
                logger.error(f"Altcoin 记录缺少必要信息 - Chain: {chain}, Address: {token_address}")
                return None

            # 从 DexScreener 获取代币信息并更新价格
            token_info = self.dex_service.get_token_info(chain, token_address)
            logger.info(f"获取到的代币信息: {token_info}")

            if token_info is not None:
                # 更新 Notion 页面
                await self._update_notion_page(page["id"], token_info)

                # 准备汇总数据
                symbol = token_info["symbol"].upper()
                current_price = token_info["price"]
                total_value = tokens_holding * current_price

                logger.info(
                    f"准备的汇总数据 - Symbol: {symbol}, Price: {current_price}, "
                    f"Tokens: {tokens_holding}, Total Value: {total_value}"
                )

                # 返回需要汇总的数据
                return {
                    "summary": {
                        symbol: {
                            "name": token_info["name"],
                            "symbol": symbol,
                            "current_price": current_price,
                            "total_tokens": tokens_holding,
                            "total_value": total_value,
                        }
                    },
                    "asset_types": {symbol: "altcoin"},
                }

            return None

        except Exception as e:
            logger.error(f"处理 Altcoin 项目时出错: {e}")
            logger.exception(e)
            return None
