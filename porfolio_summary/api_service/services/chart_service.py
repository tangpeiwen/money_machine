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

            # 如果没有持仓数据，返回空图表
            if not current_holdings:
                logger.warning("No holdings data available")
                return None

            # 获取昨日数据
            if current_data.get("has_previous_data"):
                yesterday_data = await notion_service._get_yesterday_portfolio_data()
                previous_holdings = yesterday_data.get("holdings", {}) if yesterday_data else None
            else:
                previous_holdings = None

            # 按价值排序，只包含占比大于1%的币种
            portfolio_items = [
                {"symbol": symbol, "value": float(value), "percentage": (float(value) / total_value * 100)}
                for symbol, value in current_holdings.items()
                if value and (float(value) / total_value * 100) >= 0.5  # 只保留占比大于1%的币种
            ]

            logger.info(f"portfolio_items: {portfolio_items}")

            if not portfolio_items:
                logger.warning("No valid portfolio items")
                return None

            # 按价值排序
            portfolio_items.sort(key=lambda x: x["value"], reverse=True)

            # 计算与昨日的对比
            if previous_holdings:
                for item in portfolio_items:
                    symbol = item["symbol"]
                    if symbol in previous_holdings:
                        prev_value = previous_holdings[symbol]
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
                vertical_spacing=0.1,
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
                    "font": dict(size=18),
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
                y=0.72,
                xref="paper",
                yref="paper",
                font=dict(size=18),
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

    @staticmethod
    async def create_portfolio_waterfall(current_data, previous_data=None):
        """创建投资组合瀑布图，展示每个币种的日变化"""
        logger.info("Creating portfolio waterfall chart")

        try:
            notion_service = NotionService()

            # 获取当前持仓数据
            portfolio_data = await notion_service._get_current_portfolio_values()
            current_holdings = portfolio_data.get("holdings", {})

            # 获取昨日数据
            yesterday_data = await notion_service._get_yesterday_portfolio_data()
            previous_holdings = yesterday_data.get("holdings", {}) if yesterday_data else {}

            if not current_holdings or not previous_holdings:
                logger.warning("Insufficient data for waterfall chart")
                return None

            # 计算每个币种的变化
            changes = []
            for symbol in set(current_holdings.keys()) | set(previous_holdings.keys()):
                current_value = float(current_holdings.get(symbol, 0))
                previous_value = float(previous_holdings.get(symbol, 0))
                change = current_value - previous_value

                if abs(change) >= 1:  # 只显示变化超过1美元的币种
                    changes.append(
                        {
                            "symbol": symbol,
                            "change": change,
                            "previous_value": previous_value,
                            "current_value": current_value,
                            "pct_change": (change / previous_value * 100) if previous_value != 0 else 0,
                        }
                    )

            # 按变化绝对值排序
            changes.sort(key=lambda x: abs(x["change"]), reverse=True)

            # 准备图表数据
            symbols = [item["symbol"] for item in changes]
            values = [item["change"] for item in changes]

            # 使用更柔和的颜色
            colors = ["rgba(0, 176, 80, 0.7)" if v >= 0 else "rgba(255, 44, 44, 0.7)" for v in values]

            # 创建瀑布图
            fig = go.Figure()

            # 添加零线
            fig.add_hline(y=0, line=dict(color="rgba(128, 128, 128, 0.3)", width=1, dash="dash"), layer="below")

            # 添加柱状图
            fig.add_trace(
                go.Bar(
                    name="Change",
                    x=symbols,
                    y=values,
                    marker=dict(
                        color=colors,
                        line=dict(
                            color=["rgba(0, 140, 64, 1)" if v >= 0 else "rgba(204, 35, 35, 1)" for v in values],
                            width=0.5,
                        ),
                    ),
                    text=[f"${v:+,.2f}<br>{p:+.1f}%" for v, p in zip(values, [item["pct_change"] for item in changes])],
                    textposition="outside",
                    textfont=dict(
                        size=10, color=["rgba(0, 140, 64, 1)" if v >= 0 else "rgba(204, 35, 35, 1)" for v in values]
                    ),
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        + "Change: $%{y:,.2f}<br>"
                        + "Previous: $%{customdata[0]:,.2f}<br>"
                        + "Current: $%{customdata[1]:,.2f}<br>"
                        + "Change: %{customdata[2]:+.1f}%<br>"
                        + "<extra></extra>"
                    ),
                    customdata=[
                        [item["previous_value"], item["current_value"], item["pct_change"]] for item in changes
                    ],
                )
            )

            # 更新布局
            fig.update_layout(
                title={
                    "text": (
                        f"24h Portfolio Changes by Asset<br>"
                        f"<span style='font-size:14px;color:gray'>{datetime.now().strftime('%Y-%m-%d')}</span>"
                    ),
                    "y": 0.95,
                    "x": 0.5,
                    "xanchor": "center",
                    "yanchor": "top",
                    "font": dict(size=20, color="#2F4F4F"),
                },
                width=1200,
                height=700,
                showlegend=False,
                plot_bgcolor="rgba(248,248,248,0.3)",
                paper_bgcolor="white",
                yaxis=dict(
                    title="Change in USD",
                    titlefont=dict(size=14, color="#666666"),
                    gridcolor="rgba(128,128,128,0.1)",
                    zerolinecolor="rgba(128,128,128,0.2)",
                    zerolinewidth=1,
                ),
                xaxis=dict(
                    title="Assets",
                    titlefont=dict(size=14, color="#666666"),
                    tickangle=0,
                    tickfont=dict(size=12),
                ),
                bargap=0.4,
                margin=dict(t=120, l=80, r=80, b=40),
            )

            # 添加总变化注释
            total_change = sum(values)
            total_previous = sum(item["previous_value"] for item in changes)
            total_pct_change = (total_change / total_previous * 100) if total_previous != 0 else 0

            change_color = "rgba(0, 140, 64, 1)" if total_change >= 0 else "rgba(204, 35, 35, 1)"

            fig.add_annotation(
                text=(
                    f"Total Change: <span style='color:{change_color}'>"
                    f"${total_change:+,.2f} ({total_pct_change:+.1f}%)</span>"
                ),
                x=0.5,
                y=1,
                xref="paper",
                yref="paper",
                font=dict(size=16),
                showarrow=False,
                xanchor="center",
                yanchor="bottom",
            )

            # 添加背景网格
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(128,128,128,0.1)")
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(128,128,128,0.1)")

            return fig

        except Exception as e:
            logger.error(f"Error creating portfolio waterfall chart: {e}")
            return None
