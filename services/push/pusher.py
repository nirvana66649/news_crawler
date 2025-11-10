import httpx
import datetime
import aiomysql
import json
from core.database import get_db_cursor
from core.config import push_config

# 推送函数：构造符合接口要求的请求体，自动带 Content-Type: application/json
async def push_to_user(to_user_name: str, content: str) -> bool:
    now = datetime.datetime.now()
    data = {
        "msgType": 1,
        "bizName": push_config.biz_name,
        "toType": 1,
        "title": "每天订阅推送",
        "content": content,
        "sendUserName": to_user_name,
        "sendNickName": push_config.send_nick_name,
        "sendTime": now.strftime("%Y%m%d"),
        "url": push_config.default_url,
        "img": "",
        "toUserName": to_user_name
    }

    print("🚀 正在发送给接口的完整数据:", json.dumps(data, ensure_ascii=False, indent=2))

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(push_config.api_url, json=data)
            print(f"🔁 接口响应状态: {resp.status_code}")
            try:
                print(f"📦 接口响应内容: {resp.json()}")
            except Exception:
                print(f"📦 接口响应非 JSON 内容: {resp.text}")

            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ 推送给用户 {to_user_name} 失败: {e}")
            if 'resp' in locals():
                print(f"🔁 响应状态: {resp.status_code}")
                print(f"📦 响应内容: {resp.text}")
            return False

# 批量推送任务
async def push_pending_news():
    async with get_db_cursor() as cur:
            await cur.execute("""
                SELECT s.user_id, s.to_user AS to_user_name, a.id AS article_id,
                       a.title, a.url, m.id AS match_id
                FROM user_subscriptions s
                JOIN subscription_matches m ON s.id = m.subscription_id
                JOIN news_articles a ON a.id = m.article_id
                WHERE s.is_deleted = 0 AND m.is_pushed = FALSE
                ORDER BY s.user_id, a.created_at
            """)
            rows = await cur.fetchall()

            if not rows:
                print("没有未推送的新闻")
                return {"pushed_users": 0, "pushed_articles": 0}

            user_articles = {}
            for row in rows:
                user_articles.setdefault(row['user_id'], {
                    "username": row['to_user_name'],
                    "articles": [],
                    "match_ids": []
                })['articles'].append(row)
                user_articles[row['user_id']]['match_ids'].append(row['match_id'])

            pushed_match_ids = set()
            pushed_user_count = 0

            for user_id, info in user_articles.items():
                articles = info['articles']
                to_user_name = info['username']

                # 按接口示例格式拼接 content，带“引用”关键词
                content_lines = [f"{a['title']}\n引用 {a['url']}" for a in articles]
                content_str = "\n\n".join(content_lines)

                print(f"📨 正在推送给用户 {to_user_name}，内容如下:\n{content_str}\n")

                success = await push_to_user(to_user_name, content_str)
                if success:
                    pushed_user_count += 1
                    pushed_match_ids.update(info['match_ids'])

            if pushed_match_ids:
                ids_str = ",".join(str(i) for i in pushed_match_ids)
                await cur.execute(f"UPDATE subscription_matches SET is_pushed=TRUE WHERE id IN ({ids_str})")

            return {
                "pushed_users": pushed_user_count,
                "pushed_articles": len(pushed_match_ids)
            }
