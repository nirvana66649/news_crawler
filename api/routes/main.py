"""
新闻爬虫主应用模块 - 完全重构版本
"""
from fastapi import FastAPI, Query, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import json
from typing import Dict, Any

# 本地模块导入
from core.models import StandardResponse, NewsSummaryItem, PaginatedNewsSummary
from core.database import get_db_cursor, check_db_health
from core.config import app_config, settings
from utils.logger import get_logger
from core.exceptions import DatabaseException, ValidationException
from services.monitoring import system_monitor, start_monitoring_task
from services.crawler import periodic_crawl, scheduled_push_task
from services.push import push_pending_news
from services.crawler import crawl_and_save
from services.summary import generate_user_news_summaries

# 初始化日志
logger = get_logger(__name__)

# 全局变量存储后台任务
background_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global background_tasks
    
    # 启动时执行
    logger.info("🚀 应用启动中...")
    
    try:
        # 验证配置
        if not settings.validate():
            logger.error("❌ 配置验证失败，应用无法启动")
            raise RuntimeError("配置验证失败")
        
        # 测试数据库连接
        if await check_db_health():
            logger.info("✅ 数据库连接测试成功")
        else:
            logger.warning("⚠️ 数据库连接测试失败，但继续启动")
        
        # 启动后台任务
        background_tasks.append(asyncio.create_task(periodic_crawl()))
        background_tasks.append(asyncio.create_task(scheduled_push_task()))
        background_tasks.append(asyncio.create_task(start_monitoring_task()))
        logger.info("✅ 后台任务启动成功")
        
        logger.info("🎉 应用启动完成")
        
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        raise
    
    yield
    
    # 关闭时执行
    logger.info("🔄 应用关闭中...")
    
    try:
        # 取消后台任务
        for task in background_tasks:
            if not task.done():
                logger.info(f"取消任务: {task.get_name()}")
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
        
        # 数据库使用直连模式，无需特殊关闭操作
        logger.info("✅ 数据库连接清理完成")
        
        logger.info("✅ 应用关闭完成")
        
    except Exception as e:
        logger.error(f"❌ 应用关闭时出现错误: {e}")


# 创建FastAPI应用
app = FastAPI(
    title="新闻爬虫API",
    description="智能新闻爬取、汇总和推送系统",
    version="2.0.0",
    debug=app_config.debug,
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 异常处理器 ====================

@app.exception_handler(DatabaseException)
async def database_exception_handler(request: Request, exc: DatabaseException):
    logger.error(f"数据库异常: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "show": 0, "msg": f"数据库错误: {exc.message}", "data": None}
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    logger.warning(f"参数验证异常: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"code": 400, "show": 0, "msg": exc.message, "data": None}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "show": 0, "msg": "服务器内部错误", "data": None}
    )


# ==================== API路由 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "新闻爬虫系统",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    try:
        health_status = await system_monitor.check_health()
        metrics = await system_monitor.collect_system_metrics()
        uptime = system_monitor.get_uptime()
        
        return {
            "status": health_status.status,
            "uptime_seconds": uptime.total_seconds(),
            "database": health_status.database,
            "system_metrics": metrics.to_dict(),
            "message": health_status.message,
            "timestamp": health_status.timestamp.isoformat()
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "message": str(e)}
        )


@app.get("/metrics")
async def get_metrics(minutes: int = Query(10, ge=1, le=60, description="获取最近N分钟的指标")):
    """获取系统性能指标"""
    try:
        summary = system_monitor.get_metrics_summary(minutes)
        return {
            "code": 200,
            "data": summary,
            "msg": "获取成功"
        }
    except Exception as e:
        logger.error(f"获取指标失败: {e}")
        raise HTTPException(status_code=500, detail="获取指标失败")


@app.get("/crawl/news/{user_id}/subscriptions/news", response_model=StandardResponse)
async def get_user_news(
    user_id: int,
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，最大100"),
):
    """获取用户新闻汇总"""
    # 参数验证
    if user_id <= 0:
        raise ValidationException("user_id", str(user_id), "必须是正整数")
    
    offset = (page - 1) * page_size
    logger.info(f"获取用户 {user_id} 新闻汇总: page={page}, size={page_size}")

    try:
        async with get_db_cursor() as cur:
            # 获取总数
            await cur.execute(
                "SELECT COUNT(*) AS total FROM news_summary WHERE user_id = %s",
                (user_id,)
            )
            total_result = await cur.fetchone()
            total = total_result["total"] if total_result else 0
            
            logger.debug(f"用户 {user_id} 共有 {total} 条新闻汇总")

            if total == 0:
                logger.info(f"用户 {user_id} 暂无新闻汇总")
                return StandardResponse(
                    code=404,
                    show=0,
                    msg="暂无新闻汇总",
                    data=PaginatedNewsSummary(items=[], total=0, page=page, page_size=page_size)
                )

            # 获取分页数据
            await cur.execute("""
                SELECT summary_json, summary_date
                FROM news_summary
                WHERE user_id = %s
                ORDER BY summary_date DESC
                LIMIT %s OFFSET %s
            """, (user_id, page_size, offset))
            rows = await cur.fetchall()

            items = []
            for row in rows:
                try:
                    summary_obj = json.loads(row["summary_json"])
                    summary_data = summary_obj.get("summary", {})
                    urls = summary_obj.get("urls", [])
                    summary_date = row["summary_date"].isoformat()

                    # title 拼接 summary 分类和内容
                    title_parts = []
                    for category, entries in summary_data.items():
                        combined = " ".join(entries)
                        title_parts.append(f"{category}：{combined}")
                    full_title = "\n".join(title_parts)

                    # summary 拼接 URL 列表
                    url_str = "引用链接 " + " 、 ".join(urls) if urls else ""

                    items.append(NewsSummaryItem(
                        title=full_title,
                        summary=url_str,
                        url="",  # 固定空字符串
                        date=summary_date
                    ))
                except Exception as e:
                    logger.error(f"解析用户 {user_id} 的 summary_json 失败: {e}")
                    items.append(NewsSummaryItem(
                        title="数据解析失败",
                        summary="",
                        url="",
                        date=row["summary_date"].isoformat()
                    ))

            logger.info(f"成功获取用户 {user_id} 新闻汇总: {len(items)} 条")
            return StandardResponse(
                code=200,
                show=1,
                msg="请求成功",
                data=PaginatedNewsSummary(
                    items=items,
                    total=total,
                    page=page,
                    page_size=page_size
                )
            )

    except Exception as e:
        logger.error(f"获取用户 {user_id} 新闻汇总失败: {e}", exc_info=True)
        return StandardResponse(
            code=500,
            show=0,
            msg=f"查询失败：{str(e)}",
            data=PaginatedNewsSummary(items=[], total=0, page=page, page_size=page_size)
        )


@app.post("/admin/push_now")
async def manual_push():
    """手动触发推送"""
    logger.info("收到手动推送请求")
    
    try:
        result = await push_pending_news()
        logger.info(f"手动推送完成: {result}")
        return {
            "code": 200,
            "show": 1,
            "msg": f"手动推送成功，推送用户数: {result['pushed_users']}，推送文章数: {result['pushed_articles']}",
            "data": result
        }
    except Exception as e:
        logger.error(f"手动推送失败: {e}", exc_info=True)
        return {
            "code": 500,
            "show": 0,
            "msg": f"手动推送失败: {str(e)}",
            "data": {}
        }


@app.post("/crawl_and_summarize")
async def crawl_and_summarize(request: Request):
    """手动爬取并生成汇总"""
    try:
        body = await request.json()
        subscription_id = body.get("subscription_id")
        
        if not subscription_id:
            raise ValidationException("subscription_id", "", "参数不能为空")
        
        logger.info(f"收到手动爬取请求: subscription_id={subscription_id}")

        # 先爬取
        try:
            crawl_result = await crawl_and_save(subscription_id)
            logger.info(f"爬取完成: {crawl_result}")
        except Exception as e:
            logger.error(f"爬取失败: {e}", exc_info=True)
            return {"code": 500, "msg": f"爬取失败: {str(e)}"}

        # 爬取完成后生成汇总
        try:
            await generate_user_news_summaries()
            logger.info("汇总生成完成")
        except Exception as e:
            logger.error(f"汇总生成失败: {e}", exc_info=True)
            return {"code": 500, "msg": f"汇总生成失败: {str(e)}"}

        return {
            "code": 200, 
            "msg": f"订阅 {subscription_id} 爬取并生成汇总成功",
            "data": crawl_result
        }
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"爬取和汇总操作失败: {e}", exc_info=True)
        return {"code": 500, "msg": f"操作失败: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=app_config.debug,
        log_level=app_config.log_level.lower()
    )