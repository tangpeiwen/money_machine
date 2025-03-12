from fastapi import APIRouter, HTTPException, UploadFile, File, Response
from typing import Optional
from ....services.screenshot_recognition import ScreenshotRecognitionService
from ....core.utils import TEMP_USER_ID
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/recognize")
async def recognize_assets_from_screenshot(
    screenshot: UploadFile = File(...),
    user_id: str = TEMP_USER_ID,
):
    """
    从交易所截图中识别资产

    - **screenshot**: 交易所截图文件
    """
    try:
        # 验证文件类型
        if not screenshot.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # 读取图片数据
        image_data = await screenshot.read()

        # 处理截图
        result = await ScreenshotRecognitionService.extract_assets_from_screenshot(
            image_data=image_data,
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        # 确保返回JSON
        return result

    except HTTPException as he:
        # 重新抛出HTTP异常
        raise he
    except Exception as e:
        logger.error(f"Error processing screenshot: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing screenshot: {str(e)}")
