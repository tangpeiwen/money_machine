from io import BytesIO
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

from api_service.config import settings
from api_service.services.notion_service import NotionService
from api_service.services.crypto_service import CryptoService
from api_service.services.chart_service import ChartService
from api_service.utils.logger import logger

APP = FastAPI()
notion_service = NotionService()
crypto_service = CryptoService()
chart_service = ChartService()

@APP.get("/check-and-update")
async def check_and_update():
    """检查并更新数据库中的加密货币价格"""
    logger.info("开始检查和更新加密货币价格")
    try:
        today = datetime.now().strftime("%Y-%m-%d")

        # 1. 更新主表价格并获取汇总数据
        crypto_summary, asset_types = await notion_service.update_portfolio_prices()

        # 2. 清除今天的历史记录
        await notion_service.clear_today_history(today)

        # 3. 保存新的历史记录
        updated_count = await notion_service.save_portfolio_history(
            crypto_summary, asset_types, today
        )

        return {"status": "success", "message": f"Updated {updated_count} entries"}

    except Exception as e:
        error_msg = f"更新过程中发生错误: {str(e)}"
        logger.error(error_msg)
        logger.exception(e)
        raise HTTPException(status_code=500, detail=error_msg)

@APP.get("/portfolio-summary")
async def get_portfolio_data():
    """获取投资组合数据摘要"""
    try:
        summary_data = await notion_service.get_portfolio_summary()
        return summary_data

    except Exception as e:
        logger.error(f"获取投资组合数据时出错: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@APP.get("/portfolio-chart")
async def generate_portfolio_chart():
    """生成投资组合图表"""
    try:
        # 获取投资组合摘要数据
        current_data = await notion_service.get_portfolio_summary()

        if not current_data:
            raise HTTPException(status_code=404, detail="No portfolio data found")

        # 创建图表
        fig = await chart_service.create_portfolio_donut(current_data)

        if fig is None:
            raise HTTPException(status_code=404, detail="Failed to create chart")

        # 转换为图片
        img_bytes = BytesIO()
        fig.write_image(img_bytes, format="png")
        img_bytes.seek(0)

        return Response(content=img_bytes.getvalue(), media_type="image/png")

    except Exception as e:
        logger.error(f"生成投资组合图表时出错: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))