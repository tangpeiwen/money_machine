import requests
import time
from datetime import datetime
import os
from notion_client import Client
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# API密钥配置
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
CMC_API_KEY = os.getenv('CMC_API_KEY')

# 初始化Notion客户端
notion = Client(auth=NOTION_TOKEN)

def get_crypto_price(symbol):
    """从CoinMarketCap获取加密货币价格和信息"""
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    parameters = {
        'symbol': symbol.upper(),
        'convert': 'USD'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': CMC_API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, params=parameters)
        data = response.json()
        
        if 'data' in data and symbol.upper() in data['data']:
            crypto_data = data['data'][symbol.upper()]
            return {
                'name': crypto_data['name'],
                'symbol': crypto_data['symbol'],
                'price': crypto_data['quote']['USD']['price'],
                'success': True
            }
    except Exception as e:
        print(f"获取价格时出错: {e}")
    
    return {'success': False}

def update_notion_database():
    """更新Notion数据库中的加密货币价格"""
    # 查询Notion数据库
    query = notion.databases.query(
        database_id=NOTION_DATABASE_ID,
        filter={
            "and": [
                {
                    "property": "资产类型",
                    "select": {
                        "equals": "cryptocurrency"
                    }
                },
                {
                    "property": "Address",
                    "rich_text": {
                        "is_empty": True
                    }
                }
            ]
        }
    )
    
    # 处理每条记录
    for page in query['results']:
        properties = page['properties']
        
        # 获取Name字段
        if 'Name' in properties and properties['Name'].get('title'):
            crypto_name = properties['Name']['title'][0]['text']['content']
            
            # 获取加密货币信息
            crypto_data = get_crypto_price(crypto_name)
            
            if crypto_data['success']:
                # 更新Notion页面
                notion.pages.update(
                    page_id=page['id'],
                    properties={
                        'Name': {
                            'title': [{'text': {'content': crypto_data['name']}}]
                        },
                        'Symbol': {
                            'rich_text': [{'text': {'content': crypto_data['symbol']}}]
                        },
                        'Current Price': {
                            'number': crypto_data['price']
                        },
                        'Last Updated': {
                            'date': {
                                'start': datetime.utcnow().isoformat()
                            }
                        }
                    }
                )
                print(f"已更新 {crypto_data['name']} 的价格: ${crypto_data['price']:.2f}")
                time.sleep(1)  # 避免API限制

def main():
    """主函数，定期运行更新"""
    while True:
        print(f"开始更新价格 - {datetime.now()}")
        update_notion_database()
        print("更新完成，等待下次更新...\n")
        # 等待12小时
        time.sleep(43200)  # 12小时 = 43200秒

if __name__ == "__main__":
    main() 