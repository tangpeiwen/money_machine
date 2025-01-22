from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from api_service.utils.logger import logger
from api_service.services.notion_service import NotionService


class ChartService:
    @staticmethod
    async def create_portfolio_donut(current_data, previous_data=None):
        """创建投资组合环形图，包含与昨日的对比"""
        logger.info(f"current_data: {current_data}")

        # 从 current_data 中提取总值，确保是数字类型
        try:
            total_value = float(current_data.get("total_value", 0))
        except (TypeError, ValueError):
            logger.error("Invalid total_value in current_data")
            return None

        # 如果没有持仓数据，返回空图表
        if total_value == 0:
            logger.warning("No portfolio data available")
            return None

        # 获取当前持仓数据
        try:
            # 需要从 NotionService 获取详细的持仓数据
            notion_service = NotionService()
            portfolio_data = await notion_service._get_current_portfolio_values()
            current_holdings = portfolio_data.get("holdings", {})
            asset_types = portfolio_data.get("asset_types", {})  # 获取资产类型信息
            logger.info(f"portfolio_data: {portfolio_data}")

            # 如果没有持仓数据，返回空图表
            if not current_holdings:
                logger.warning("No holdings data available")
                return None

            # 合并 altcoin 数据
            merged_holdings = {}
            altcoin_total = 0

            for symbol, value in current_holdings.items():
                if asset_types.get(symbol) == "altcoin":
                    altcoin_total += float(value)
                else:
                    merged_holdings[symbol] = value

            if altcoin_total > 0:
                merged_holdings["Altcoins"] = altcoin_total

            # 获取昨日数据
            if current_data.get("has_previous_data"):
                yesterday_data = await notion_service._get_yesterday_portfolio_data()
                previous_holdings = yesterday_data.get("holdings", {}) if yesterday_data else None
            else:
                previous_holdings = None

            # 按价值排序
            portfolio_items = [
                {"symbol": symbol, "value": float(value), "percentage": (float(value) / total_value * 100)}
                for symbol, value in merged_holdings.items()
                if value  # 跳过零值
            ]

            logger.info(f"portfolio_items: {portfolio_items}")

            if not portfolio_items:
                logger.warning("No valid portfolio items")
                return None

            portfolio_items.sort(key=lambda x: x["value"], reverse=True)

            # 计算与昨日的对比
            if previous_holdings:
                # 合并昨日的 altcoin 数据
                merged_previous = {}
                prev_altcoin_total = 0

                for symbol, value in previous_holdings.items():
                    if asset_types.get(symbol) == "altcoin":
                        prev_altcoin_total += float(value)
                    else:
                        merged_previous[symbol] = value

                if prev_altcoin_total > 0:
                    merged_previous["Altcoins"] = prev_altcoin_total

                for item in portfolio_items:
                    symbol = item["symbol"]
                    if symbol in merged_previous:
                        prev_value = merged_previous[symbol]
                        item["change"] = item["value"] - prev_value
                        item["change_pct"] = ((item["value"] / prev_value) - 1) * 100 if prev_value else 0
                    else:
                        item["change"] = item["value"]
                        item["change_pct"] = 100

            # 准备图表数据
            labels = [f"{item['symbol']}<br>{item['percentage']:.3f}%" for item in portfolio_items]
            values = [item["value"] for item in portfolio_items]

            # 准备标签文本
            custom_text = [
                f"{item['symbol']}<br>{(item['value']/total_value*100):.2f}%"
                if item["value"] / total_value >= 0.05
                else item["symbol"]
                for item in portfolio_items
            ]

            # 创建子图布局
            fig = make_subplots(
                rows=2,
                cols=1,
                row_heights=[0.6, 0.4],  # 调整比例
                vertical_spacing=0.2,
                specs=[[{"type": "pie"}], [{"type": "table"}]],
            )

            # 添加环形图
            fig.add_trace(
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.6,
                    textinfo="text",  # 使用自定义文本
                    textposition="outside",
                    text=custom_text,  # 使用自定义文本列表
                    textfont=dict(size=12),  # 调整字体大小
                    marker=dict(colors=px.colors.qualitative.Vivid, line=dict(color="white", width=2)),
                    showlegend=False,
                    pull=[0.05 if value / total_value < 0.05 else 0 for value in values],  # 小值略微分离
                ),
                row=1,
                col=1,
            )

            # 准备表格数据
            table_headers = ["Asset", "Value ($)", "Allocation (%)", "Change ($)", "Change (%)"]
            table_data = [
                [
                    f"<b>{item['symbol']}</b>",
                    f"{item['value']:,.2f}",
                    f"{item['percentage']:.2f}%",
                    f"{item.get('change', 0):+,.2f}" if previous_holdings else "-",
                    f"{item.get('change_pct', 0):+.1f}%" if previous_holdings else "-",
                ]
                for item in portfolio_items
            ]

            # 添加表格
            fig.add_trace(
                go.Table(
                    header=dict(
                        values=[f"<b>{h}</b>" for h in table_headers],
                        font=dict(size=14, color="black"),
                        align="left",
                        fill_color="#E5ECF6",
                    ),
                    cells=dict(
                        values=list(zip(*table_data)),
                        font=dict(
                            size=12,
                            color=[
                                ["black"] * len(portfolio_items),  # Asset 列
                                ["black"] * len(portfolio_items),  # Value 列
                                ["black"] * len(portfolio_items),  # Allocation 列
                                # Change ($) 列
                                ["green" if item.get("change", 0) >= 0 else "red" for item in portfolio_items],
                                # Change (%) 列
                                ["green" if item.get("change_pct", 0) >= 0 else "red" for item in portfolio_items],
                            ],
                        ),
                        align=["left", "right", "right", "right", "right"],
                        height=30,
                        fill_color=[["white", "#F9F9F9"] * (len(portfolio_items) // 2 + 1)],
                    ),
                ),
                row=2,
                col=1,
            )

            # 更新布局
            fig.update_layout(
                title={
                    "text": f"Crypto Portfolio Allocation<br>{datetime.now().strftime('%Y-%m-%d')}",
                    "y": 0.98,
                    "x": 0.5,
                    "xanchor": "center",
                    "yanchor": "top",
                    "font": dict(size=16),
                },
                width=1000,  # 增加宽度
                height=1200,  # 增加高度
                showlegend=False,
                margin=dict(t=80, l=120, r=120, b=20, pad=10),  # 增加左右边距，为标签留出空间
            )

            # 在环形图中心添加总价值
            fig.add_annotation(
                text=f"<b>Total Value</b><br>${total_value:,.2f}",
                x=0.5,
                y=0.7,
                xref="paper",
                yref="paper",
                font=dict(size=16),
                showarrow=False,
                xanchor="center",
                yanchor="middle",
            )

            # 更新表格样式
            fig.update_traces(
                cells=dict(
                    height=30,  # 增加单元格高度
                    font=dict(size=13),  # 增加字体大小
                ),
                header=dict(
                    height=35,  # 增加表头高度
                    font=dict(size=14),  # 增加字体大小
                ),
                selector=dict(type="table"),
            )

            return fig
        except Exception as e:
            logger.error(f"Error creating portfolio donut chart: {e}")
            return None
