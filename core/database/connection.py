"""
数据库连接管理模块 - 简化版本
"""
import aiomysql
from typing import AsyncContextManager
from contextlib import asynccontextmanager
from core.config import db_config
from utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def get_db_connection() -> AsyncContextManager[aiomysql.Connection]:
    """获取数据库连接的上下文管理器"""
    conn = None
    try:
        conn = await aiomysql.connect(
            host=db_config.host,
            port=db_config.port,
            user=db_config.user,
            password=db_config.password,
            db=db_config.database,
            autocommit=db_config.autocommit
        )
        yield conn
    except Exception as e:
        logger.error(f"数据库连接错误: {e}")
        raise
    finally:
        if conn:
            conn.close()


@asynccontextmanager
async def get_db_cursor(cursor_class=None) -> AsyncContextManager[aiomysql.Cursor]:
    """获取数据库游标的上下文管理器"""
    if cursor_class is None:
        cursor_class = aiomysql.DictCursor
    
    async with get_db_connection() as conn:
        cursor = None
        try:
            cursor = await conn.cursor(cursor_class)
            yield cursor
        finally:
            if cursor:
                await cursor.close()


async def check_db_health() -> bool:
    """检查数据库连接健康状态"""
    try:
        async with get_db_cursor() as cursor:
            await cursor.execute("SELECT 1")
            result = await cursor.fetchone()
            return result is not None
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return False

