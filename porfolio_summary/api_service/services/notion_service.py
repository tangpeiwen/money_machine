from datetime import datetime, timedelta
from collections import defaultdict

from notion_client import Client

from api_service.config import settings
from api_service.utils.logger import logger
from api_service.services.crypto_service import CryptoService  # 添加这个导入


class NotionService:
    def __init__(self):
        self.client = Client(auth=settings.NOTION_TOKEN)
        self.crypto_service = CryptoService()

    async def update_portfolio_prices(self):
        """更新主表中的加密货币价格并返回汇总数据"""
        try:
            query = self.client.databases.query(
                database_id=settings.NOTION_DATABASE_ID,
                filter={"property": "资产类型", "select": {"equals": "cryptocurrency"}},
            )

            crypto_summary = {}
            asset_types = {}

            for page in query["results"]:
                result = await self._process_portfolio_item(page)
                if result:
                    crypto_summary.update(result["summary"])
                    asset_types.update(result["asset_types"])

            return crypto_summary, asset_types

        except Exception as e:
            logger.error(f"更新投资组合价格时出错: {e}")
            raise

    async def _process_portfolio_item(self, page):
        """处理单个投资组合项目"""
        try:
            properties = page["properties"]
            name, symbol = self._extract_name_symbol(properties)
            asset_type = self._extract_asset_type(properties)

            if symbol:
                asset_types = {symbol.upper(): asset_type}

            logger.info(f"处理记录 - Name: {name}, Symbol: {symbol}")

            crypto_data = await self._get_crypto_data(name, symbol)
            if not crypto_data["success"]:
                return None

            # 更新主表
            await self._update_notion_page(page["id"], crypto_data)

            # 准备汇总数据
            search_key = crypto_data["symbol"].upper()
            current_price = crypto_data["price"]
            tokens_holding = properties.get("Tokens Holding", {}).get("number", 0)
            average_cost = properties.get("Cost", {}).get("number", 0)
            cost_basis = tokens_holding * average_cost if tokens_holding and average_cost else 0
            total_value = tokens_holding * current_price

            return {
                "summary": {
                    search_key: {  # 使用 search_key 作为键
                        "name": crypto_data["name"],
                        "symbol": crypto_data["symbol"].upper(),
                        "current_price": current_price,
                        "total_tokens": tokens_holding,
                        "total_value": total_value,
                        "total_cost_basis": cost_basis,
                    }
                },
                "asset_types": asset_types,
            }

        except Exception as e:
            logger.error(f"处理投资组合项目时出错: {e}")
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
        for search_key, data in crypto_summary.items():
            if data["total_tokens"] > 0:
                try:
                    # 计算加权平均成本
                    weighted_avg_cost = data["total_cost_basis"] / data["total_tokens"]

                    # 使用对应的资产类型
                    asset_type = asset_types.get(search_key, "cryptocurrency")

                    self.client.pages.create(
                        parent={"database_id": settings.NOTION_HISTORY_DATABASE_ID},
                        properties={
                            "Date": {"date": {"start": today}},
                            "Symbol": {"rich_text": [{"text": {"content": data["symbol"]}}]},
                            "资产类型": {"select": {"name": asset_type}},
                            "Current Price": {"number": round(data["current_price"], 8)},
                            "Tokens Holding": {"number": round(data["total_tokens"], 8)},
                            "Holding Values": {"number": round(data["total_value"], 4)},
                            "Cost": {"number": round(weighted_avg_cost, 4)},
                        },
                    )

                    updated_count += 1
                    logger.info(
                        f"成功保存 {search_key} 的汇总数据: "
                        f"总持仓: {data['total_tokens']:.8f}, "
                        f"总价值: ${data['total_value']:.2f}, "
                        f"加权平均成本: ${weighted_avg_cost:.4f}"
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
                filter={"property": "资产类型", "select": {"equals": "cryptocurrency"}},
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
    
    async def update_single_crypto_price(self, page_id: str) -> dict:
        """更新单个加密货币的价格数据"""
        try:
            # 获取页面数据
            page = self.client.pages.retrieve(page_id=page_id)
            properties = page["properties"]
            
            # 提取名称和符号
            name, symbol = self._extract_name_symbol(properties)
            logger.info(f"更新单个记录 - Name: {name}, Symbol: {symbol}")
            
            # 获取价格数据
            crypto_data = await self._get_crypto_data(name, symbol)
            if not crypto_data["success"]:
                raise Exception(f"无法获取 {name}({symbol}) 的价格数据")
            
            # 只更新 Current Price
            self.client.pages.update(
                page_id=page_id,
                properties={
                    "Current Price": {"number": crypto_data["price"]}
                }
            )
            
            logger.info(f"更新价格 - {name}({symbol}): ${crypto_data['price']}")
            
            return {
                "status": "success",
                "data": {
                    "name": name,
                    "symbol": symbol,
                    "current_price": crypto_data["price"]
                }
            }
            
        except Exception as e:
            logger.error(f"更新单个加密货币价格时出错: {e}")
            logger.exception(e)
            raise

    async def update_new_crypto_records(self) -> list:
        """检查并更新新添加的加密货币记录"""
        try:
            # 查询最近添加的加密货币记录
            query = self.client.databases.query(
                database_id=settings.NOTION_DATABASE_ID,
                filter={
                    "and": [
                        {
                            "property": "资产类型",
                            "select": {
                                "equals": "cryptocurrency"
                            }
                        },
                        {
                            "property": "Current Price",
                            "number": {
                                "is_empty": True
                            }
                        }
                    ]
                }
            )

            updated_records = []
            for page in query["results"]:
                try:
                    # 提取名称和符号
                    name, symbol = self._extract_name_symbol(page["properties"])
                    
                    # 获取价格数据
                    crypto_data = await self._get_crypto_data(name, symbol)
                    if not crypto_data["success"]:
                        continue
                    
                    # 更新所有相关字段
                    self.client.pages.update(
                        page_id=page["id"],
                        properties={
                            "Current Price": {"number": crypto_data["price"]},
                            "Symbol": {"rich_text": [{"text": {"content": crypto_data["symbol"]}}]},
                            "Name": {"title": [{"text": {"content": crypto_data["name"]}}]}
                        }
                    )
                    
                    updated_records.append({
                        "name": crypto_data["name"],  # 使用获取到的标准名称
                        "symbol": crypto_data["symbol"],  # 使用获取到的标准符号
                        "price": crypto_data["price"]
                    })
                    
                    logger.info(f"更新新记录 - {crypto_data['name']}({crypto_data['symbol']}): ${crypto_data['price']}")
                    
                except Exception as e:
                    logger.error(f"更新记录时出错: {str(e)}")
                    continue
            
            return updated_records
            
        except Exception as e:
            logger.error(f"检查新记录时出错: {e}")
            logger.exception(e)
            raise

    