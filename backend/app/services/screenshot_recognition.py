import os
import base64
import tempfile
from PIL import Image
from openai import OpenAI
import json
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# 初始化豆包客户端
client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=os.environ.get("ARK_API_KEY"),
)


class ScreenshotRecognitionService:
    @staticmethod
    def preprocess_image(image_data: bytes, max_size=(1024, 1024)):
        """预处理图片以减少大小和token消耗"""
        # 从二进制数据创建图像
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(image_data)
            temp_file_path = temp_file.name

        # 打开图像并调整大小
        image = Image.open(temp_file_path)
        image.thumbnail(max_size)

        # 保存为临时文件
        processed_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        processed_path = processed_file.name
        image.save(processed_path, "JPEG", quality=85)
        processed_file.close()

        # 删除原始临时文件
        os.remove(temp_file_path)

        return processed_path

    @staticmethod
    def encode_image(image_path: str) -> str:
        """将图片转为Base64编码"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    @staticmethod
    async def extract_assets_from_screenshot(image_data: bytes) -> Dict:
        """从交易所截图中提取加密货币资产信息"""
        try:
            # 检查API密钥
            if not os.environ.get("ARK_API_KEY"):
                logger.error("ARK_API_KEY not set in environment variables")
                return {"error": "API key not configured"}

            # 预处理图片
            processed_image = ScreenshotRecognitionService.preprocess_image(image_data)

            # 将图片转为Base64编码
            base64_image = ScreenshotRecognitionService.encode_image(processed_image)

            # 构建提示词
            prompt = f"""
            请分析以下截图，并提取以下信息，以JSON格式返回：
            1. 交易所名称（如果可以识别）
            2. 对于截图中显示的每种加密货币资产：
               - 资产符号（例如BTC、ETH）
               - 资产名称（如果有）
               - 持有数量
               - 当前价格
               - 24小时价格变化百分比
            根据提取的内容自行判这是crpyto/stock还是其他资产类型。

            请仅返回有效的JSON对象，格式如下：
            {{
              "资产类型": "cryptocurrency",
              "assets": [
                {{
                  "symbol": "BTC",
                  "name": "Bitcoin",
                  "amount": 0.12345,
                  "current_price": 10000,
                  "percent_change_24h": 1.23
                }},
                ...
              ]
            }}
            """

            try:
                # 调用豆包API
                response = client.chat.completions.create(
                    model="doubao-1-5-vision-pro-32k-250115",  # 使用豆包Vision Pro模型
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                                },
                            ],
                        }
                    ],
                    response_format={"type": "json_object"},  # 指定返回JSON格式
                )

                # 提取响应内容
                result = response.choices[0].message.content

                # 解析JSON
                parsed_result = json.loads(result)

                # 标准化输出格式
                standardized_result = {"asset_type": parsed_result.get("资产类型", "cryptocurrency"), "assets": []}

                for asset in parsed_result.get("assets", []):
                    standardized_asset = {
                        "symbol": asset.get("symbol", "").upper(),
                        "name": asset.get("name", ""),
                        "amount": asset.get("amount", 0),
                        "current_price": asset.get("current_price", 0),
                        "percent_change_24h": asset.get("percent_change_24h", 0),
                    }
                    standardized_result["assets"].append(standardized_asset)

                return standardized_result
            except Exception as api_error:
                logger.error(f"API call error: {str(api_error)}")
                return {"error": f"API processing error: {str(api_error)}"}

        except Exception as e:
            logger.error(f"Error in extract_assets_from_screenshot: {str(e)}", exc_info=True)
            return {"error": str(e)}
        finally:
            # 清理临时文件
            if "processed_image" in locals() and os.path.exists(processed_image):
                os.remove(processed_image)
