import os
from typing import Dict, Any
from datetime import datetime, timedelta
import logging
import requests
import base64

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from notion_client import Client
from dotenv import load_dotenv
import uvicorn
import plotly.graph_objects as go
from io import BytesIO
import pandas as pd
from collections import defaultdict
import plotly.express as px
from plotly.subplots import make_subplots


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'crypto_updates_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# API密钥配置
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
NOTION_HISTORY_DATABASE_ID = os.getenv('NOTION_HISTORY_DATABASE_ID')
CMC_API_KEY = os.getenv('CMC_API_KEY')

# 初始化应用
app = FastAPI()
notion = Client(auth=NOTION_TOKEN)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_crypto_price(query: str, query_type: str = 'symbol') -> Dict[str, Any]:
    """获取加密货币价格信息
    Args:
        query: 搜索词（可以是 symbol 或 name）
        query_type: 'symbol' 或 'slug'，表示搜索类型
    """
    logger.info(f"正在获取加密货币信息，搜索类型: {query_type}, 搜索词: {query}")
    
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    parameters = {
        query_type: query.lower() if query_type == 'slug' else query.upper(),
        'convert': 'USD'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': CMC_API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, params=parameters)
        data = response.json()
        
        if 'data' in data and data['data']:
            crypto_data = list(data['data'].values())[0]
            result = {
                'name': crypto_data['name'],
                'symbol': crypto_data['symbol'],
                'price': crypto_data['quote']['USD']['price'],
                'success': True
            }
            logger.info(f"成功获取价格数据: {result}")
            return result
            
        logger.warning(f"未找到匹配的加密货币: {query}")
            
    except Exception as e:
        logger.error(f"获取加密货币信息时出错: {e}")
        logger.exception(e)
    
    return {'success': False}

def get_property_text(properties: dict, property_name: str) -> str:
    """安全地获取 Notion 属性的文本内容
    
    Args:
        properties: Notion 页面的属性字典
        property_name: 属性名称
    
    Returns:
        str: 属性的文本内容，如果不存在则返回空字符串
    """
    prop = properties.get(property_name, {})
    if prop_type := prop.get('type'):
        if prop_type == 'title':
            rich_text_list = prop.get('title', [])
        else:
            rich_text_list = prop.get('rich_text', [])
        
        if rich_text_list and len(rich_text_list) > 0:
            return rich_text_list[0].get('text', {}).get('content', '')
    return ''

@app.get("/check-and-update")
async def check_and_update():
    """检查并更新数据库中的加密货币价格，同时保存历史记录"""
    logger.info("开始检查和更新加密货币价格")
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 1. 首先更新主表的价格数据
        query = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "资产类型",
                "select": {
                    "equals": "cryptocurrency"
                }
            }
        )

        # 更新主表中的价格
        crypto_summary = {}
        asset_types = {}  # 存储资产类型
        
        for page in query['results']:
            properties = page['properties']
            name = ''
            symbol = ''
            
            # 获取 Name
            name_data = properties.get('Name', {}).get('title', [])
            if name_data and name_data[0].get('text'):
                name = name_data[0]['text'].get('content', '').strip()
            
            # 获取 Symbol
            symbol_data = properties.get('Symbol', {}).get('rich_text', [])
            if symbol_data and symbol_data[0].get('text'):
                symbol = symbol_data[0]['text'].get('content', '').strip()
            
            # 获取资产类型
            asset_type = properties.get('资产类型', {}).get('select', {}).get('name', 'cryptocurrency')
            if symbol:
                asset_types[symbol.upper()] = asset_type
            
            logger.info(f"处理记录 - Name: {name}, Symbol: {symbol}")

            # 初始化 crypto_data 为失败状态
            crypto_data = {'success': False}
            
            # 1. 首先尝试使用 Symbol
            if symbol:
                logger.info(f"使用 Symbol 搜索: {symbol}")
                crypto_data = get_crypto_price(symbol, 'symbol')
            
            # 2. 如果 Symbol 搜索失败且有 Name，尝试使用 Name 作为 slug
            if not crypto_data['success'] and name:
                logger.info(f"Symbol 搜索失败，使用 Name 作为 slug 搜索: {name}")
                crypto_data = get_crypto_price(name, 'slug')
            
            # 3. 如果 slug 搜索也失败，尝试使用 Name 作为 symbol
            if not crypto_data['success'] and name:
                logger.info(f"Slug 搜索失败，尝试使用 Name 作为 symbol 搜索: {name}")
                crypto_data = get_crypto_price(name, 'symbol')
            
            # 如果所有搜索方式都失败
            if not crypto_data['success']:
                logger.warning(f"所有搜索方式都失败 - Name: {name}, Symbol: {symbol}")
                continue
                
            if crypto_data['success']:
                # 更新主表中的价格、Name 和 Symbol
                update_properties = {
                    "Current Price": {
                        "number": crypto_data['price']
                    },
                    "Symbol": {
                        "rich_text": [{
                            "text": {
                                "content": crypto_data['symbol']
                            }
                        }]
                    },
                    "Name": {
                        "title": [{
                            "text": {
                                "content": crypto_data['name']
                            }
                        }]
                    }
                }
                
                notion.pages.update(
                    page_id=page['id'],
                    properties=update_properties
                )
                logger.info(f"更新主表 - 原始: {name}({symbol}) -> 更新后: {crypto_data['name']}({crypto_data['symbol']}), "
                          f"价格: ${crypto_data['price']}")
                
                # 为汇总准备数据
                search_key = crypto_data['symbol'].upper()
                current_price = crypto_data['price']
                tokens_holding = properties.get('Tokens Holding', {}).get('number', 0)
                average_cost = properties.get('Cost', {}).get('number', 0)
                
                if search_key not in crypto_summary:
                    crypto_summary[search_key] = {
                        'name': crypto_data['name'],
                        'symbol': crypto_data['symbol'].upper(),
                        'current_price': current_price,
                        'total_tokens': 0,
                        'total_value': 0,
                        'total_cost_basis': 0
                    }
                
                cost_basis = tokens_holding * average_cost if tokens_holding and average_cost else 0
                crypto_summary[search_key]['total_tokens'] += tokens_holding
                crypto_summary[search_key]['total_value'] += (tokens_holding * current_price)
                crypto_summary[search_key]['total_cost_basis'] += cost_basis
                
                logger.info(f"更新汇总数据 - {search_key}: 总持仓 {crypto_summary[search_key]['total_tokens']:.8f}, "
                          f"总价值 ${crypto_summary[search_key]['total_value']:.2f}")

        # 2. 保存历史记录前，先删除当天已有的记录
        try:
            # 查询当天的记录
            existing_records = notion.databases.query(
                database_id=NOTION_HISTORY_DATABASE_ID,
                filter={
                    "property": "Date",
                    "date": {
                        "equals": today
                    }
                }
            )
            
            # 删除当天的所有记录
            for record in existing_records['results']:
                notion.pages.update(
                    page_id=record['id'],
                    archived=True  # 这会将页面移到回收站
                )
            
            if existing_records['results']:
                logger.info(f"已删除 {len(existing_records['results'])} 条当天的历史记录")
        
        except Exception as e:
            logger.error(f"删除当天历史记录时出错: {e}")
            # 继续执行，不中断流程

        # 保存新的历史记录
        updated_count = 0
        for search_key, data in crypto_summary.items():
            if data['total_tokens'] > 0:
                data['weighted_avg_cost'] = (
                    data['total_cost_basis'] / 
                    data['total_tokens']
                )
                
                try:
                    # 使用对应的资产类型
                    asset_type = asset_types.get(search_key, "cryptocurrency")
                    
                    notion.pages.create(
                        parent={"database_id": NOTION_HISTORY_DATABASE_ID},
                        properties={
                            "Date": {
                                "date": {"start": today}
                            },
                            "Symbol": {
                                "rich_text": [{
                                    "text": {"content": data['symbol']}
                                }]
                            },
                            "资产类型": {
                                "select": {
                                    "name": asset_type
                                }
                            },
                            "Current Price": {
                                "number": data['current_price']
                            },
                            "Tokens Holding": {
                                "number": round(data['total_tokens'], 8)
                            },
                            "Holding Values": {
                                "number": round(data['total_value'], 4)
                            },
                            "Cost": {
                                "number": round(data['weighted_avg_cost'], 4)
                            }
                        }
                    )
                    
                    updated_count += 1
                    logger.info(f"成功保存 {search_key} 的汇总数据: "
                              f"总持仓: {data['total_tokens']:.8f}, "
                              f"总价值: ${data['total_value']:.2f}, "
                              f"加权平均成本: ${data['weighted_avg_cost']:.4f}")
                    
                except Exception as e:
                    logger.error(f"保存 {search_key} 的汇总数据时出错: {e}")
                    continue

        return {
            "status": "success",
            "message": f"Updated {updated_count} entries"
        }
        
    except Exception as e:
        error_msg = f"更新过程中发生错误: {str(e)}"
        logger.error(error_msg)
        logger.exception(e)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
async def health_check():
    """健康检查端点"""
    logger.debug("收到健康检查请求")
    return {"status": "healthy"}

# 添加错误处理中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求"""
    start_time = datetime.now()
    response = await call_next(request)
    duration = datetime.now() - start_time
    logger.info(
        f"请求: {request.method} {request.url.path} - "
        f"状态码: {response.status_code} - "
        f"处理时间: {duration.total_seconds():.3f}s"
    )
    return response

@app.get("/portfolio-data")
async def get_portfolio_data():
    """获取投资组合数据摘要"""
    try:
        # 获取当前数据
        current_query = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "资产类型",
                "select": {
                    "equals": "cryptocurrency"
                }
            }
        )
        
        # 计算当前总值
        current_total = 0
        portfolio_data = defaultdict(float)
        
        for page in current_query['results']:
            properties = page['properties']
            symbol = properties.get('Symbol', {}).get('rich_text', [{}])[0].get('text', {}).get('content', 'Unknown')
            holding_value = properties.get('Holding Values', {}).get('formula', {}).get('number', 0)
            
            if holding_value:
                portfolio_data[symbol] += holding_value
                current_total += holding_value
        
        # 获取昨天的数据（从历史数据库）
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_query = notion.databases.query(
            database_id=NOTION_HISTORY_DATABASE_ID,
            filter={
                "property": "Date",
                "date": {
                    "equals": yesterday
                }
            }
        )
        
        # 计算昨天的总值
        yesterday_total = 0
        if yesterday_query['results']:
            for page in yesterday_query['results']:
                props = page['properties']
                holding_value = props.get('Holding Values', {}).get('formula', {}).get('number', 0)
                yesterday_total += holding_value
            
            # 计算变化
            change_amount = current_total - yesterday_total
            change_percentage = (change_amount / yesterday_total * 100) if yesterday_total else 0
        else:
            change_amount = None
            change_percentage = None
        
        # 准备数据摘要
        summary_data = {
            "total_value": round(current_total, 2),
            "has_previous_data": bool(yesterday_query['results']),
            "change_amount": round(change_amount, 2) if change_amount is not None else None,
            "change_percentage": round(change_percentage, 2) if change_percentage is not None else None,
            "date": datetime.now().strftime('%Y-%m-%d')
        }
        
        logger.info(f"生成投资组合摘要: {summary_data}")
        
        return summary_data
        
    except Exception as e:
        logger.error(f"获取投资组合数据时出错: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))
    

async def get_current_portfolio_data():
    """获取当前投资组合数据"""
    try:
        # 查询主数据库
        query = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "资产类型",
                "select": {
                    "equals": "cryptocurrency"
                }
            }
        )
        
        # 汇总每个币种的总价值
        portfolio_data = {}
        asset_types = {}

        for page in query['results']:
            properties = page['properties']
            
            # 获取 Symbol
            symbol_data = properties.get('Symbol', {}).get('rich_text', [])
            if not symbol_data:
                continue
            symbol = symbol_data[0]['text'].get('content', '').strip()

            # 获取资产类型
            asset_type = properties.get('资产类型', {}).get('select', {}).get('name', '')
            if asset_type:
                asset_types[symbol] = asset_type
            
            # 获取当前价值
            current_price = properties.get('Current Price', {}).get('number', 0)
            tokens_holding = properties.get('Tokens Holding', {}).get('number', 0)
            value = current_price * tokens_holding
            
            # 累加相同币种的价值
            if symbol in portfolio_data:
                portfolio_data[symbol] += value
            else:
                portfolio_data[symbol] = value
        
        logger.info(f"获取当前投资组合数据 - 币种: {len(portfolio_data)}")
        
        return portfolio_data, asset_types
        
    except Exception as e:
        logger.error(f"获取当前投资组合数据时出错: {e}")
        raise

async def get_previous_portfolio_data():
    """获取昨日投资组合数据"""
    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        # 查询历史数据库
        query = notion.databases.query(
            database_id=NOTION_HISTORY_DATABASE_ID,
            filter={
                "property": "Date",
                "date": {
                    "equals": yesterday
                }
            }
        )
        
        # 获取昨日数据
        portfolio_data = {}
        for page in query['results']:
            properties = page['properties']
            logger.info(f"获取昨日投资组合数据 - 币种: {properties}")
            
            # 获取 Symbol
            symbol_data = properties.get('Symbol', {}).get('rich_text', [])
            if not symbol_data:
                continue
            symbol = symbol_data[0]['text'].get('content', '').strip()
            
            # 获取价值
            holding_value = properties.get('Holding Values', {}).get('formula', {}).get('number', 0)
            logger.info(f"获取昨日投资组合数据 - 币种: {symbol}, 价值: {holding_value}")
            portfolio_data[symbol] = holding_value
        
        return portfolio_data
        
    except Exception as e:
        logger.error(f"获取昨日投资组合数据时出错: {e}")
        raise

async def save_portfolio_history(today, crypto_summary, asset_types):
    """保存投资组合历史记录"""
    updated_count = 0
    for search_key, data in crypto_summary.items():
        if data['total_tokens'] > 0:
            data['weighted_avg_cost'] = (
                data['total_cost_basis'] / 
                data['total_tokens']
            )
            try:
                # 使用对应的资产类型
                asset_type = asset_types.get(search_key, "cryptocurrency")  # 默认值以防万一
                
                notion.pages.create(
                    parent={"database_id": NOTION_HISTORY_DATABASE_ID},
                    properties={
                        "Date": {
                            "date": {"start": today}
                        },
                        "Symbol": {
                            "rich_text": [{
                                "text": {"content": data['symbol'] if data['symbol'] else data['name']}
                            }]
                        },
                        "资产类型": {
                            "select": {
                                "name": asset_type
                            }
                        },
                        "Current Price": {
                            "number": data['current_price']
                        },
                        "Tokens Holding": {
                            "number": round(data['total_tokens'], 8)
                        },
                        "Holding Values": {
                            "number": round(data['total_value'], 4)
                        },
                        "Cost": {
                            "number": round(data['weighted_avg_cost'], 4)
                        }
                    }
                )
                
                updated_count += 1
                logger.info(f"成功保存 {search_key} 的汇总数据: "
                          f"总持仓: {data['total_tokens']:.8f}, "
                          f"总价值: ${data['total_value']:.2f}, "
                          f"加权平均成本: ${data['weighted_avg_cost']:.4f}")
                
            except Exception as e:
                logger.error(f"保存 {search_key} 的汇总数据时出错: {e}")
                continue
                
    return updated_count


@app.get("/portfolio-chart")
async def generate_portfolio_chart():
    """生成投资组合图表"""
    try:
        # 获取当前和历史数据
        current_data, _ = await get_current_portfolio_data()  # 使用解构赋值
        previous_data = await get_previous_portfolio_data()
        
        if not current_data:
            raise HTTPException(status_code=404, detail="No portfolio data found")
        
        # 创建图表
        fig = create_portfolio_donut(current_data, previous_data)
        
        # 转换为图片
        img_bytes = BytesIO()
        fig.write_image(img_bytes, format='png')
        img_bytes.seek(0)
        
        return Response(content=img_bytes.getvalue(), media_type="image/png")
        
    except Exception as e:
        logger.error(f"生成投资组合图表时出错: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

def create_portfolio_donut(current_data, previous_data=None):
    """创建投资组合环形图，包含与昨日的对比"""
    # 计算总价值
    total_value = sum(value for value in current_data.values())
    
    # 按价值排序
    portfolio_items = [
        {
            'symbol': symbol,
            'value': value,
            'percentage': (value / total_value * 100)
        }
        for symbol, value in current_data.items()
    ]
    portfolio_items.sort(key=lambda x: x['value'], reverse=True)
    
    # 计算与昨日的对比
    if previous_data:
        for item in portfolio_items:
            symbol = item['symbol']
            if symbol in previous_data:
                prev_value = previous_data[symbol]
                item['change'] = item['value'] - prev_value
                item['change_pct'] = ((item['value'] / prev_value) - 1) * 100 if prev_value else 0
            else:
                item['change'] = item['value']
                item['change_pct'] = 100
    
    # 准备图表数据
    labels = [f"{item['symbol']}<br>{item['percentage']:.1f}%" for item in portfolio_items]
    values = [item['value'] for item in portfolio_items]
    
    # 创建子图布局，左侧放环形图，右侧放表格
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.1,
        specs=[[{"type": "pie"}], [{"type": "table"}]]
    )
    
    # 添加环形图
    fig.add_trace(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.6,
            textinfo='label',  # 只显示标签
            textposition='outside',  # 标签位置在外部
            # textfont=dict(size=14, color='black'),  # 增加字体大小
            marker=dict(
                colors=px.colors.qualitative.Vivid,
                line=dict(color='white', width=2)  # 添加间隔
            ),
            showlegend=False
        ),
        row=1, col=1
    )
    
    # 准备表格数据
    table_headers = ['Asset', 'Value ($)', 'Change ($)', 'Change (%)']
    table_data = [
        [
            f"<b>{item['symbol']}</b>",  # 加粗币种符号
            f"{item['value']:,.2f}",
            # 使用不同颜色显示涨跌，但不使用 span 标签
            f"{item.get('change', 0):+,.2f}" if previous_data else "-",
            f"{item.get('change_pct', 0):+.1f}%" if previous_data else "-"
        ]
        for item in portfolio_items
    ]

    # 添加表格
    fig.add_trace(
        go.Table(
            header=dict(
                values=[f"<b>{h}</b>" for h in table_headers],  # 加粗表头
                font=dict(size=14, color='black'),
                align='left',
                fill_color='#E5ECF6'
            ),
            cells=dict(
                values=list(zip(*table_data)),
                font=dict(
                    size=12,
                    # 为变化值设置颜色
                    color=[
                        ['black'] * len(portfolio_items),  # Asset 列
                        ['black'] * len(portfolio_items),  # Value 列
                        # Change ($) 列
                        ['green' if item.get('change', 0) >= 0 else 'red' 
                         for item in portfolio_items],
                        # Change (%) 列
                        ['green' if item.get('change_pct', 0) >= 0 else 'red' 
                         for item in portfolio_items]
                    ]
                ),
                align='left',
                height=25,
                fill_color=[['white', '#F9F9F9'] * (len(portfolio_items)//2 + 1)]
            )
        ),
        row=2, col=1
    )

    # 在环形图中心添加总价值
    fig.add_annotation(
        text=f"<b>Total Value</b><br>${total_value:,.2f}",
        x=0.5,  # x坐标居中
        y=0.7,  # 由于现在是上下布局，需要调整y坐标
        xref="paper",  # 使用paper参考系统
        yref="paper",  # 使用paper参考系统
        font=dict(size=14),
        showarrow=False,
        xanchor='center',  # 水平居中对齐
        yanchor='middle'   # 垂直居中对齐
    )
    
    # 更新布局
    fig.update_layout(
        title={
            'text': f"Crypto Portfolio Allocation<br>{datetime.now().strftime('%Y-%m-%d')}",
            'y':0.98,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=16)
        },
        width=800,  # 增加整体宽度
        height=1000,  # 增加整体高度
        showlegend=False,
        margin=dict(t=60, l=40, r=40, b=20,pad=10)  # 减小边距
        # paper_bgcolor='white',  # 设置背景色
        # plot_bgcolor='white',
        # margin=dict(t=100, l=50, r=50, b=50)  # 调整边距
    )
    
    return fig

if __name__ == "__main__":
    logger.info("启动服务器...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 