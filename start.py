#!/usr/bin/env python3
"""
新闻爬虫系统启动脚本
"""
import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_dependencies():
    """检查依赖是否安装"""
    required_packages = [
        'fastapi', 'uvicorn', 'aiomysql', 'httpx', 
        'pytz', 'pydantic', 'psutil'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ 缺少依赖包: {', '.join(missing)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    print("✅ 所有依赖包已安装")
    return True


def check_config():
    """检查配置文件"""
    env_file = project_root / '.env'
    example_file = project_root / 'env.example'
    
    if not env_file.exists():
        if example_file.exists():
            print("⚠️  .env文件不存在，请复制env.example并配置:")
            print(f"cp {example_file} {env_file}")
        else:
            print("❌ 配置文件不存在")
        return False
    
    print("✅ 配置文件存在")
    return True


async def test_database():
    """测试数据库连接"""
    try:
        from core.database import check_db_health
        is_healthy = await check_db_health()
        if is_healthy:
            print("✅ 数据库连接正常")
            return True
        else:
            print("❌ 数据库连接失败")
            return False
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 新闻爬虫系统启动检查")
    print("=" * 40)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查配置
    if not check_config():
        sys.exit(1)
    
    # 测试数据库（异步）
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        db_ok = loop.run_until_complete(test_database())
        loop.close()
        
        if not db_ok:
            print("请检查数据库配置和连接")
            sys.exit(1)
    except Exception as e:
        print(f"数据库测试跳过: {e}")
    
    print("\n✅ 系统检查通过，启动应用...")
    print("=" * 40)
    
    # 启动应用
    import uvicorn
    from core.config import app_config
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=app_config.debug,
        log_level=app_config.log_level.lower()
    )


if __name__ == "__main__":
    main()
