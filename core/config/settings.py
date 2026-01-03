"""
配置管理模块 - 统一管理所有配置项
"""
from pydantic import validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    model_config = SettingsConfigDict(env_prefix="DB_", env_ignore_empty=True)

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

    @validator('host', pre=True, always=True)
    def default_host_if_empty(cls, v):
        return v or "localhost"

    @validator('user', pre=True, always=True)
    def default_user_if_empty(cls, v):
        return v or "root"

    @validator('database', pre=True, always=True)
    def default_database_if_empty(cls, v):
        return v or "news"
    
class CrawlerConfig(BaseSettings):
    """爬虫配置"""
    model_config = SettingsConfigDict(env_prefix="CRAWLER_", env_ignore_empty=True)

    webhook_url: str = "http://localhost:5678/webhook/test"
    timeout: int = 600
    batch_size: int = 2
    batch_delay: int = 5  # 批次间延迟(秒)
    retry_attempts: int = 3
    retry_delay: int = 10  # 重试延迟(秒)


class SchedulerConfig(BaseSettings):
    """调度器配置"""
    model_config = SettingsConfigDict(env_prefix="SCHEDULER_", env_ignore_empty=True)

    crawl_interval: int = 86400  # 爬取间隔(秒) - 24小时
    error_sleep: int = 300  # 错误后等待时间(秒)


class AppConfig(BaseSettings):
    """应用配置"""
    model_config = SettingsConfigDict(env_prefix="APP_", env_ignore_empty=True)

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
    
class Settings:
    """全局配置类"""
    def __init__(self):
        self.database = DatabaseConfig()
        self.crawler = CrawlerConfig()
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
scheduler_config = settings.scheduler
app_config = settings.app

# 支持从 core.config 导入
__all__ = [
    'settings',
    'db_config',
    'crawler_config', 
    'scheduler_config',
    'app_config'
]
