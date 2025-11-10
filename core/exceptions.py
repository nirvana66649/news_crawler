"""
自定义异常类模块
"""


class NewsRawlerBaseException(Exception):
    """新闻爬虫基础异常类"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class DatabaseException(NewsRawlerBaseException):
    """数据库相关异常"""
    pass


class CrawlerException(NewsRawlerBaseException):
    """爬虫相关异常"""
    pass


class NoArticlesException(CrawlerException):
    """无文章异常"""
    def __init__(self, subscription_id: str):
        super().__init__(
            message=f"订阅 {subscription_id} 没有获取到文章",
            error_code="NO_ARTICLES"
        )
        self.subscription_id = subscription_id


class SummaryException(NewsRawlerBaseException):
    """摘要生成异常"""
    pass


class PushException(NewsRawlerBaseException):
    """推送相关异常"""
    pass


class ConfigurationException(NewsRawlerBaseException):
    """配置相关异常"""
    pass


class RateLimitException(CrawlerException):
    """请求频率限制异常"""
    def __init__(self, retry_after: int = None):
        super().__init__(
            message="请求频率过快，已被限制",
            error_code="RATE_LIMIT"
        )
        self.retry_after = retry_after


class TimeoutException(NewsRawlerBaseException):
    """超时异常"""
    def __init__(self, operation: str, timeout: int):
        super().__init__(
            message=f"操作 {operation} 超时 ({timeout}秒)",
            error_code="TIMEOUT"
        )
        self.operation = operation
        self.timeout = timeout


class ValidationException(NewsRawlerBaseException):
    """数据验证异常"""
    def __init__(self, field: str, value: str, reason: str):
        super().__init__(
            message=f"字段 {field} 的值 '{value}' 验证失败: {reason}",
            error_code="VALIDATION_ERROR"
        )
        self.field = field
        self.value = value
        self.reason = reason
