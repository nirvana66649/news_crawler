import json
import httpx
import aiomysql
import datetime
from core.database import get_db_cursor
from core.config import summary_config

async def generate_user_news_summaries():
    async with get_db_cursor() as cur:
            # 查找今日有文章匹配的所有用户
            await cur.execute("""
                SELECT DISTINCT s.user_id
                FROM user_subscriptions s
                JOIN subscription_matches m ON s.id = m.subscription_id
                JOIN news_articles a ON a.id = m.article_id
                WHERE DATE(a.created_at) = CURDATE()
            """)
            users = await cur.fetchall()

    if not users:
        print("📭 今日无用户匹配新闻，跳过摘要生成")
        return

    async with httpx.AsyncClient(timeout=600.0) as client:
        for user in users:
            user_id = user["user_id"]
            async with get_db_cursor() as cur:
                    # 获取该用户今天匹配的文章
                    await cur.execute("""
                        SELECT a.title, a.summary, a.url, a.created_at AS date
                        FROM user_subscriptions s
                        JOIN subscription_matches m ON s.id = m.subscription_id
                        JOIN news_articles a ON a.id = m.article_id
                        WHERE s.user_id = %s AND DATE(a.created_at) = CURDATE()
                    """, (user_id,))
                    articles = await cur.fetchall()

            if not articles:
                print(f"📭 用户 {user_id} 今日无匹配文章，跳过")
                continue

            # 转换 datetime 对象为字符串
            serialized_articles = []
            for article in articles:
                serialized_article = dict(article)
                if isinstance(serialized_article['date'], datetime.datetime):
                    serialized_article['date'] = serialized_article['date'].isoformat()
                serialized_articles.append(serialized_article)

            model_input = {
                "code": 200,
                "show": 1,
                "msg": "请求成功",
                "data": {
                    "items": serialized_articles,
                    "total": len(serialized_articles),
                    "page": 1,
                    "page_size": len(serialized_articles)
                }
            }

            try:
                resp = await client.post(summary_config.endpoint, json=model_input)
                resp.raise_for_status()  # 确保 HTTP 请求成功
                resp_json = resp.json()
                data_to_save = (
                    resp_json[0]["data"] if isinstance(resp_json, list) else resp_json.get("data", {})
                )

                # 验证 data_to_save 格式
                if not isinstance(data_to_save.get("summary", {}), dict) or not isinstance(data_to_save.get("urls", []), list):
                    print(f"❌ 用户 {user_id} 摘要格式错误: {data_to_save}")
                    continue

                # 定义序列化函数处理可能的 datetime 对象
                def serialize_datetime(obj):
                    if isinstance(obj, datetime.datetime):
                        return obj.isoformat()
                    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

                summary_json_str = json.dumps(data_to_save, ensure_ascii=False, default=serialize_datetime)
                summary_date = datetime.date.today()

                async with get_db_cursor() as cur:
                        try:
                            # 使用别名避免 VALUES 警告
                            await cur.execute("""
                                INSERT INTO news_summary (user_id, summary_json, summary_date)
                                VALUES (%s, %s, %s) AS new
                                ON DUPLICATE KEY UPDATE
                                  summary_json = new.summary_json,
                                  created_at = CURRENT_TIMESTAMP
                            """, (user_id, summary_json_str, summary_date))
                            print(f"✅ 用户 {user_id} 的摘要保存成功: {summary_json_str[:100]}...")
                        except aiomysql.Error as db_error:
                            print(f"❌ 用户 {user_id} 数据库插入失败: {db_error}")
                            continue

            except Exception as e:
                print(f"❌ 用户 {user_id} 摘要生成失败: {e}")
                continue
