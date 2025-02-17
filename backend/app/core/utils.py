import uuid


def generate_uuid() -> str:
    """生成 UUID 字符串"""
    return str(uuid.uuid4())


# 临时用户 ID（开发测试用）
TEMP_USER_ID = "123e4567-e89b-12d3-a456-426614174000"
