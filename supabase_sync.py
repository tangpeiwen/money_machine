import json
import asyncio
import uuid
from datetime import datetime
import argparse
import sys
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# 如果这是一个独立脚本，你需要设置 Supabase 凭证
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 如果你想集成到现有项目中，可以使用以下导入方式
# from backend.app.core.config import settings
# from backend.app.core.database import db


async def sync_cryptocurrencies_to_supabase(json_file, batch_size=100):
    """
    将 JSON 文件中的加密货币数据同步到 Supabase，保持顺序并添加序号

    Args:
        json_file: JSON 文件路径
        batch_size: 批量插入的大小

    Returns:
        同步统计信息
    """
    # 初始化统计信息
    stats = {"total": 0, "new_added": 0, "skipped": 0, "failed": 0}

    try:
        # 读取 JSON 文件
        with open(json_file, "r") as f:
            cryptos = json.load(f)

        stats["total"] = len(cryptos)
        print(f"从 {json_file} 读取了 {stats['total']} 个加密货币")

        # 初始化 Supabase 客户端
        # 如果使用现有项目的配置，可以用：supabase = db.get_supabase_client()
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # 获取现有的加密货币符号列表和最大序号
        try:
            result = supabase.table("cryptocurrencies").select("symbol,rank").order("rank.desc").limit(1).execute()
            existing_symbols = set()

            # 获取当前最大序号
            max_rank = 0
            if result.data:
                max_rank = result.data[0].get("rank", 0) or 0

            # 获取所有现有符号
            all_symbols_result = supabase.table("cryptocurrencies").select("symbol").execute()
            existing_symbols = {item["symbol"] for item in all_symbols_result.data}

            print(f"数据库中已有 {len(existing_symbols)} 个加密货币，最大序号为 {max_rank}")
        except Exception as e:
            print(f"获取现有加密货币列表时出错: {e}")
            existing_symbols = set()
            max_rank = 0

        # 准备要插入的数据
        now = datetime.utcnow().isoformat()
        crypto_data = []

        # 当前序号
        current_rank = max_rank

        for crypto in cryptos:
            try:
                symbol = crypto["symbol"].upper()

                # 检查是否已存在
                if symbol in existing_symbols:
                    stats["skipped"] += 1
                    continue

                # 增加序号
                current_rank += 1

                # 添加到待插入列表
                crypto_data.append(
                    {
                        "id": str(uuid.uuid4()),
                        "symbol": symbol,
                        "name": crypto["name"],
                        "logo_url": crypto.get("logo_url", ""),
                        "rank": current_rank,  # 添加序号
                        "created_at": now,
                        "updated_at": now,
                    }
                )

                # 标记为已存在，避免在同一批次中重复
                existing_symbols.add(symbol)

            except Exception as e:
                print(f"处理加密货币 {crypto.get('symbol', '未知')} 时出错: {e}")
                stats["failed"] += 1

        # 批量插入数据
        if crypto_data:
            try:
                # 分批插入
                for i in range(0, len(crypto_data), batch_size):
                    batch = crypto_data[i : i + batch_size]
                    insert_result = supabase.table("cryptocurrencies").insert(batch).execute()

                    if insert_result.data:
                        batch_added = len(insert_result.data)
                        stats["new_added"] += batch_added
                        print(
                            f"成功插入 {batch_added} 个新加密货币 (批次 {i//batch_size + 1}/{(len(crypto_data)-1)//batch_size + 1})"
                        )
                    else:
                        print(f"批量插入未返回数据 (批次 {i//batch_size + 1})")
            except Exception as e:
                print(f"批量插入加密货币时出错: {e}")
                stats["failed"] += len(crypto_data) - stats["new_added"]

        print(f"同步完成，统计信息: 总计 {stats['total']}, 新增 {stats['new_added']}, 跳过 {stats['skipped']}, 失败 {stats['failed']}")
        return stats

    except Exception as e:
        print(f"同步过程中出错: {e}")
        return {
            "error": str(e),
            "total": stats["total"],
            "new_added": stats["new_added"],
            "skipped": stats["skipped"],
            "failed": stats["failed"],
        }


async def reset_and_sync_cryptocurrencies(json_file, batch_size=100):
    """
    清空表并重新同步所有加密货币，按照 JSON 文件中的顺序分配序号
    """
    try:
        # 初始化 Supabase 客户端
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # 清空表
        print("正在清空加密货币表...")
        supabase.table("cryptocurrencies").delete().neq("id", "dummy").execute()

        # 读取 JSON 文件
        with open(json_file, "r") as f:
            cryptos = json.load(f)

        print(f"从 {json_file} 读取了 {len(cryptos)} 个加密货币")

        # 准备要插入的数据
        now = datetime.utcnow().isoformat()
        crypto_data = []

        for i, crypto in enumerate(cryptos, 1):
            try:
                symbol = crypto["symbol"].upper()

                # 添加到待插入列表，使用索引作为序号
                crypto_data.append(
                    {
                        "id": str(uuid.uuid4()),
                        "symbol": symbol,
                        "name": crypto["name"],
                        "logo_url": crypto.get("logo_url", ""),
                        "rank": i,  # 使用索引作为序号
                        "created_at": now,
                        "updated_at": now,
                    }
                )

            except Exception as e:
                print(f"处理加密货币 {crypto.get('symbol', '未知')} 时出错: {e}")

        # 批量插入数据
        total_added = 0
        if crypto_data:
            try:
                # 分批插入
                for i in range(0, len(crypto_data), batch_size):
                    batch = crypto_data[i : i + batch_size]
                    insert_result = supabase.table("cryptocurrencies").insert(batch).execute()

                    if insert_result.data:
                        batch_added = len(insert_result.data)
                        total_added += batch_added
                        print(
                            f"成功插入 {batch_added} 个加密货币 (批次 {i//batch_size + 1}/{(len(crypto_data)-1)//batch_size + 1})"
                        )
                    else:
                        print(f"批量插入未返回数据 (批次 {i//batch_size + 1})")
            except Exception as e:
                print(f"批量插入加密货币时出错: {e}")

        print(f"重置并同步完成，共插入 {total_added} 个加密货币")
        return {"total": len(cryptos), "added": total_added}

    except Exception as e:
        print(f"重置并同步过程中出错: {e}")
        return {"error": str(e)}


async def main():
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="将加密货币 JSON 数据同步到 Supabase")
    parser.add_argument("json_file", help="JSON 文件路径")
    parser.add_argument("--batch-size", type=int, default=100, help="批量插入的大小")
    parser.add_argument("--reset", action="store_true", help="清空表并重新同步所有数据")

    args = parser.parse_args()

    # 执行同步
    if args.reset:
        await reset_and_sync_cryptocurrencies(args.json_file, args.batch_size)
    else:
        await sync_cryptocurrencies_to_supabase(args.json_file, args.batch_size)


if __name__ == "__main__":
    asyncio.run(main())
