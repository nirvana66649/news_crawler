"""
新闻爬虫模块 - 优化版本
"""
import asyncio
import httpx
import datetime
from typing import List, Dict, Any, Optional
from core.database import get_db_cursor, get_db_transaction_cursor
import aiomysql
import pytz
from core.config import crawler_config, app_config
from utils.logger import get_logger
from core.exceptions import NoArticlesException, CrawlerException, DatabaseException, TimeoutException

logger = get_logger(__name__)


def _to_shanghai_time(dt: Optional[datetime.datetime], tz: pytz.timezone) -> Optional[datetime.datetime]:
    """将时间转换为上海时区"""
    if dt is None:
        return None
    # 如果没有时区，用 Asia/Shanghai 进行本地化；如果已有时区，转换到 Asia/Shanghai
    return tz.localize(dt) if dt.tzinfo is None else dt.astimezone(tz)


async def fetch_due_subscriptions() -> List[str]:
    """获取到期需要爬取的订阅列表"""
    async with get_db_cursor() as cur:
            tz = pytz.timezone("Asia/Shanghai")
            now = datetime.datetime.now(tz)

            # 1️⃣ 获取每个用户最近创建的最多 3 条订阅
            await cur.execute(
                """
                SELECT id, user_id, last_crawled_at, frequency_type, frequency_value, created_at FROM (
                    SELECT *,
                        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) AS rn
                    FROM user_subscriptions
                    WHERE is_deleted = 0
                ) t
                WHERE rn <= 3
                """
            )
            latest_subs = await cur.fetchall()

            user_latest_map = {}         # user_id -> List[subscription_row]
            user_latest_due_map = {}     # user_id -> List[到期的最近订阅]

            for row in latest_subs:
                user_id = row["user_id"]
                sid = row["id"]
                user_latest_map.setdefault(user_id, []).append(row)

                last = row['last_crawled_at']
                freq_type = row['frequency_type']
                freq_val = row['frequency_value']
                due = False

                if last is None:
                    due = True  # 新订阅
                else:
                    last = _to_shanghai_time(last, tz)
                    delta = (now - last).total_seconds()
                    needed_seconds = freq_val * 86400 if freq_type == "day" else freq_val * 7 * 86400
                    due = delta >= needed_seconds

                if due:
                    user_latest_due_map.setdefault(user_id, []).append(row)

            # ✅ 改进日志输出
            print("🔍 用户最近订阅分析:")
            for uid, rows in user_latest_map.items():
                never_crawled = [r['id'] for r in rows if r['last_crawled_at'] is None]
                overdue = [r['id'] for r in user_latest_due_map.get(uid, []) if r['last_crawled_at'] is not None]

                print(f"🧑 用户 {uid}:")
                if never_crawled:
                    print(f"   - 新订阅（从未爬取）: {never_crawled}")
                if overdue:
                    print(f"   - 新订阅中超时的: {overdue}")
                if not never_crawled and not overdue:
                    print(f"   - 无需爬取的新订阅")

            # 2️⃣ 获取所有订阅（包括老的）
            await cur.execute(
                """
                SELECT id, user_id, last_crawled_at, frequency_type, frequency_value, created_at
                FROM user_subscriptions
                WHERE is_deleted = 0
                """
            )
            all_subs = await cur.fetchall()

            user_all_map = {}
            for s in all_subs:
                user_all_map.setdefault(s["user_id"], []).append(s)

            final_due_ids = set()

            for user_id, all_user_subs in user_all_map.items():
                latest_due_rows = user_latest_due_map.get(user_id, [])
                latest_due_ids = [r['id'] for r in latest_due_rows]
                latest_ids = {r['id'] for r in user_latest_map.get(user_id, [])}

                if len(latest_due_ids) >= 3:
                    final_due_ids.update(latest_due_ids[:3])
                    print(f"✅ 用户 {user_id} 已满3条新订阅，不补老: {latest_due_ids[:3]}")
                    continue

                # 还差几条
                need = 3 - len(latest_due_ids)
                old_due_subs = []

                for s in all_user_subs:
                    if s['id'] in latest_ids:
                        continue  # 跳过最近3条
                    last = s['last_crawled_at']
                    freq_type = s['frequency_type']
                    freq_val = s['frequency_value']
                    due = False
                    if last is None:
                        due = True
                    else:
                        last = _to_shanghai_time(last, tz)
                        delta = (now - last).total_seconds()
                        needed_seconds = freq_val * 86400 if freq_type == "day" else freq_val * 7 * 86400
                        due = delta >= needed_seconds
                    if due:
                        old_due_subs.append(s)

                old_due_subs.sort(key=lambda x: x['created_at'], reverse=True)
                supplemental_ids = [s['id'] for s in old_due_subs[:need]]

                final_ids = latest_due_ids + supplemental_ids
                final_due_ids.update(final_ids)

                print(f"✅ 用户 {user_id} 最终爬取订阅: {final_ids}")

            return list(final_due_ids)


async def crawl_subscription(subscription_id: str) -> List[Dict[str, Any]]:
    """爬取单个订阅的新闻数据"""
    try:
        timeout = httpx.Timeout(crawler_config.timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info(f"开始爬取订阅: {subscription_id}")
            
            resp = await client.post(
                crawler_config.webhook_url,
                json={"subscription_id": subscription_id}
            )
            
            if resp.status_code != 200:
                logger.warning(f"请求失败 {subscription_id}: HTTP {resp.status_code}")
                raise CrawlerException(f"HTTP请求失败: {resp.status_code}")
            
            if not resp.content:
                logger.warning(f"响应内容为空 {subscription_id}")
                return []
            
            try:
                return resp.json()
            except Exception as e:
                logger.error(f"JSON解析失败 {subscription_id}: {e}")
                logger.debug(f"响应内容: {resp.text[:500]}...")
                raise CrawlerException(f"JSON解析失败: {e}")
                
    except httpx.TimeoutException:
        logger.error(f"请求超时 {subscription_id}: {crawler_config.timeout}秒")
        raise TimeoutException("crawl_subscription", crawler_config.timeout)
    except Exception as e:
        logger.error(f"爬取订阅失败 {subscription_id}: {e}")
        raise

async def save_news_articles(articles: List[Dict[str, Any]], cur: Optional[aiomysql.Cursor] = None) -> List[int]:
    """保存新闻文章到数据库"""
    if not articles:
        logger.warning("没有文章需要保存")
        return []
    
    article_ids = []

    async def _run(cursor: aiomysql.Cursor) -> List[int]:
        for article in articles:
            url = article.get('url')
            if not url:
                logger.warning(f"文章缺少URL，跳过: {article.get('title', 'Unknown')}")
                continue

            title = article.get('title', '')
            summary = article.get('summary', '')

            try:
                await cursor.execute(
                    """
                    INSERT INTO news_articles (title, summary, url)
                    VALUES (%s, %s, %s)
                    """,
                    (title, summary, url),
                )
                article_id = cursor.lastrowid
                logger.debug(f"新文章已保存: ID={article_id}, Title={title[:50]}...")

            except aiomysql.IntegrityError:
                await cursor.execute("SELECT id FROM news_articles WHERE url = %s", (url,))
                result = await cursor.fetchone()
                if result:
                    article_id = result.get("id") if isinstance(result, dict) else result[0]
                    logger.debug(f"文章已存在: ID={article_id}, Title={title[:50]}...")
                else:
                    logger.error(f"无法获取现有文章ID: {url}")
                    continue

            except Exception as e:
                logger.error(f"保存文章失败: {e}, URL: {url}")
                raise DatabaseException(f"保存文章失败: {e}")

            article_ids.append(article_id)

        return article_ids

    if cur is not None:
        await _run(cur)
    else:
        async with get_db_cursor() as cursor:
            await _run(cursor)
    
    logger.info(f"成功保存/获取 {len(article_ids)} 篇文章")
    return article_ids
    
async def save_subscription_matches(
    subscription_id: str,
    article_ids: List[int],
    cur: Optional[aiomysql.Cursor] = None,
) -> int:
    """保存订阅匹配关系"""
    if not article_ids:
        logger.warning(f"订阅 {subscription_id} 没有文章需要匹配")
        return 0
    
    saved_count = 0

    async def _run(cursor: aiomysql.Cursor) -> int:
        nonlocal saved_count
        for article_id in article_ids:
            try:
                await cursor.execute(
                    """
                    INSERT INTO subscription_matches (subscription_id, article_id)
                    VALUES (%s, %s)
                    """,
                    (subscription_id, article_id),
                )
                saved_count += 1
                logger.debug(f"订阅匹配已保存: subscription={subscription_id}, article={article_id}")

            except aiomysql.IntegrityError:
                logger.debug(f"匹配关系已存在: subscription={subscription_id}, article={article_id}")
                continue
            except Exception as e:
                logger.error(f"保存匹配关系失败: {e}")
                raise DatabaseException(f"保存匹配关系失败: {e}")

        return saved_count

    if cur is not None:
        await _run(cur)
    else:
        async with get_db_cursor() as cursor:
            await _run(cursor)
    
    logger.info(f"订阅 {subscription_id} 新增匹配关系 {saved_count} 条")
    return saved_count

async def update_last_crawled(subscription_id: str, cur: Optional[aiomysql.Cursor] = None) -> bool:
    """更新订阅的最后爬取时间"""
    try:
        async def _run(cursor: aiomysql.Cursor) -> bool:
            await cursor.execute(
                """
                UPDATE user_subscriptions SET last_crawled_at=NOW() WHERE id=%s
                """,
                (subscription_id,),
            )

            if cursor.rowcount > 0:
                logger.debug(f"订阅 {subscription_id} 爬取时间已更新")
                return True

            logger.warning(f"订阅 {subscription_id} 不存在或未更新")
            return False

        if cur is not None:
            return await _run(cur)

        async with get_db_cursor() as cursor:
            return await _run(cursor)
                
    except Exception as e:
        logger.error(f"更新爬取时间失败: {e}")
        raise DatabaseException(f"更新爬取时间失败: {e}")

# 执行函数
async def crawl_and_save(subscription_id: str) -> Dict[str, Any]:
    """爬取并保存单个订阅的新闻数据"""
    logger.info(f"开始爬取订阅: {subscription_id}")
    
    try:
        # 1. 爬取数据
        data = await crawl_subscription(subscription_id)
        
        # 2. 提取文章列表
        articles = []
        if isinstance(data, list) and data and 'articles' in data[0]:
            articles = data[0]['articles']
        elif isinstance(data, dict) and 'articles' in data:
            articles = data['articles']
        
        logger.info(f"订阅 {subscription_id} 返回 {len(articles)} 条文章")
        
        if not articles:
            raise NoArticlesException(subscription_id)

        async with get_db_transaction_cursor() as cur:
            article_ids = await save_news_articles(articles, cur=cur)
            if not article_ids:
                raise NoArticlesException(subscription_id)

            match_count = await save_subscription_matches(subscription_id, article_ids, cur=cur)
            await update_last_crawled(subscription_id, cur=cur)
        
        result = {
            "subscription_id": subscription_id,
            "articles_count": len(articles),
            "saved_articles": len(article_ids),
            "new_matches": match_count,
            "status": "success"
        }
        
        logger.info(f"订阅 {subscription_id} 爬取完成: {result}")
        return result
        
    except Exception as e:
        logger.error(f"订阅 {subscription_id} 爬取失败: {e}")
        raise
