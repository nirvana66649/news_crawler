"""
配置管理模块 - 统一管理所有配置项
"""
import os
from typing import Optional
from pydantic import validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "news"
    autocommit: bool = True
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('端口号必须在 1-65535 之间')
        return v
    
    class Config:
        env_prefix = "DB_"


class CrawlerConfig(BaseSettings):
    """爬虫配置"""
    webhook_url: str = "http://localhost:8080/webhook/test"
    timeout: int = 600
    batch_size: int = 2
    batch_delay: int = 5  # 批次间延迟(秒)
    retry_attempts: int = 3
    retry_delay: int = 10  # 重试延迟(秒)
    
    class Config:
        env_prefix = "CRAWLER_"


class SummaryConfig(BaseSettings):
    """摘要服务配置"""
    endpoint: str = "http://localhost:8080/webhook/summary"
    timeout: int = 600
    
    class Config:
        env_prefix = "SUMMARY_"


class PushConfig(BaseSettings):
    """推送服务配置"""
    api_url: str = "http://172.18.80.195/api/focusMessage/sendBizMessage"
    timeout: int = 30
    biz_name: str = "订阅助手"
    send_nick_name: str = "宋健"
    default_url: str = "https://www.baidu.com"
    
    class Config:
        env_prefix = "PUSH_"


class SchedulerConfig(BaseSettings):
    """调度器配置"""
    crawl_interval: int = 86400  # 爬取间隔(秒) - 24小时
    push_hour: int = 8  # 推送时间(小时)
    push_minute: int = 0  # 推送时间(分钟)
    error_sleep: int = 300  # 错误后等待时间(秒)
    
    class Config:
        env_prefix = "SCHEDULER_"


class AppConfig(BaseSettings):
    """应用配置"""
    debug: bool = False
    log_level: str = "INFO"
    timezone: str = "Asia/Shanghai"
    cors_origins: list = ["*"]
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'日志级别必须是: {valid_levels}')
        return v.upper()
    
    class Config:
        env_prefix = "APP_"


class Settings:
    """全局配置类"""
    def __init__(self):
        self.database = DatabaseConfig()
        self.crawler = CrawlerConfig()
        self.summary = SummaryConfig()
        self.push = PushConfig()
        self.scheduler = SchedulerConfig()
        self.app = AppConfig()
    
    def validate(self) -> bool:
        """验证配置是否完整"""
        try:
            # 检查必需的配置项
            required_checks = [
                (self.database.host, "数据库主机地址未配置"),
                (self.database.user, "数据库用户名未配置"),
                (self.database.database, "数据库名称未配置"),
                (self.crawler.webhook_url, "爬虫Webhook URL未配置"),
                (self.summary.endpoint, "摘要服务端点未配置"),
                (self.push.api_url, "推送API URL未配置"),
            ]
            
            for value, error_msg in required_checks:
                if not value:
                    raise ValueError(error_msg)
            
            return True
        except Exception as e:
            print(f"配置验证失败: {e}")
            return False


# 全局配置实例
settings = Settings()

# 导出各个配置对象
db_config = settings.database
crawler_config = settings.crawler
summary_config = settings.summary
push_config = settings.push
scheduler_config = settings.scheduler
app_config = settings.app

# 支持从 core.config 导入
__all__ = [
    'settings',
    'db_config',
    'crawler_config', 
    'summary_config',
    'push_config',
    'scheduler_config',
    'app_config'
]
