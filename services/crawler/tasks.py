import asyncio
from .crawler import fetch_due_subscriptions, crawl_and_save
import datetime
import pytz

# 单个爬取任务封装（附带失败重试收集）
async def crawl_and_save_with_flag(subscription_id, failed_list):
    try:
        await crawl_and_save(subscription_id)
    except Exception as e:
        print(f"❌ Crawl failed for subscription {subscription_id}: {e}")
        failed_list.append(subscription_id)

# 分批执行，每次最多 n 个并发
async def batch_run(sub_ids, batch_size):
    failed = []
    for i in range(0, len(sub_ids), batch_size):
        batch = sub_ids[i:i + batch_size]
        print(f"📦 处理订阅批次: {batch}")
        tasks = [crawl_and_save_with_flag(sid, failed) for sid in batch]
        await asyncio.gather(*tasks)

        # 休息5秒，防止频繁访问
        print("⏸️ 批次处理完毕，休息5秒...")
        await asyncio.sleep(5)
    return failed

# 自动爬虫主循环
async def periodic_crawl():
    print("✅ periodic_crawl() 启动了")
    tz = pytz.timezone("Asia/Shanghai")

    while True:
        try:
            now = datetime.datetime.now(tz)
            print(f"\n🕒 周期启动时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            due_subs = await fetch_due_subscriptions()
            if not due_subs:
                print("⏳ 当前无订阅需要爬取，休眠 5 分钟...")
                await asyncio.sleep(300)
                continue

            print(f"📊 本轮总订阅数: {len(due_subs)}，每批最多2个")

            # 每批2个执行
            failed_subs = await batch_run(due_subs, batch_size=2)

            # 重试失败
            if failed_subs:
                print(f"🔁 重试失败订阅: {failed_subs}")
                await batch_run(failed_subs, batch_size=2)

            print("✅ 本轮爬取结束，等待 24 小时")
            await asyncio.sleep(86400)
        except Exception as loop_error:
            print(f"❌ periodic_crawl 循环异常: {loop_error}")
            import traceback as _tb
            _tb.print_exc()
            # 防止异常导致任务退出，等待5分钟后继续下一轮
            await asyncio.sleep(300)
