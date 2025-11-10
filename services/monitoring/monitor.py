"""
系统监控和健康检查模块
"""
import asyncio
import time
import psutil
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from core.database import check_db_health, get_db_cursor
from utils.logger import get_logger
from core.config import app_config

logger = get_logger(__name__)


@dataclass
class SystemMetrics:
    """系统性能指标"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available: int  # MB
    disk_usage_percent: float
    disk_free: int  # GB
    active_connections: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HealthStatus:
    """健康状态"""
    status: str  # healthy, warning, critical
    database: bool
    memory_ok: bool
    disk_ok: bool
    cpu_ok: bool
    message: str
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.metrics_history = []
        self.max_history = 100  # 保留最近100条记录
        
        # 健康检查阈值
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 85.0,
            'memory_warning': 80.0,
            'memory_critical': 90.0,
            'disk_warning': 80.0,
            'disk_critical': 90.0,
        }
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """收集系统性能指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available // (1024 * 1024)  # MB
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free = disk.free // (1024 * 1024 * 1024)  # GB
            
            # 数据库连接数（简化版本）
            active_connections = await self._get_db_connections()
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available=memory_available,
                disk_usage_percent=disk_usage_percent,
                disk_free=disk_free,
                active_connections=active_connections
            )
            
            # 保存到历史记录
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            raise
    
    async def _get_db_connections(self) -> int:
        """获取数据库连接数"""
        try:
            async with get_db_cursor() as cur:
                await cur.execute("SHOW STATUS LIKE 'Threads_connected'")
                result = await cur.fetchone()
                return int(result['Value']) if result else 0
        except Exception:
            return 0
    
    async def check_health(self) -> HealthStatus:
        """执行健康检查"""
        try:
            # 收集当前指标
            metrics = await self.collect_system_metrics()
            
            # 检查数据库
            db_healthy = await check_db_health()
            
            # 检查各项指标
            cpu_ok = metrics.cpu_percent < self.thresholds['cpu_critical']
            memory_ok = metrics.memory_percent < self.thresholds['memory_critical']
            disk_ok = metrics.disk_usage_percent < self.thresholds['disk_critical']
            
            # 确定整体状态
            if not db_healthy:
                status = "critical"
                message = "数据库连接失败"
            elif not (cpu_ok and memory_ok and disk_ok):
                status = "critical"
                issues = []
                if not cpu_ok:
                    issues.append(f"CPU使用率过高: {metrics.cpu_percent:.1f}%")
                if not memory_ok:
                    issues.append(f"内存使用率过高: {metrics.memory_percent:.1f}%")
                if not disk_ok:
                    issues.append(f"磁盘使用率过高: {metrics.disk_usage_percent:.1f}%")
                message = "; ".join(issues)
            elif (metrics.cpu_percent > self.thresholds['cpu_warning'] or
                  metrics.memory_percent > self.thresholds['memory_warning'] or
                  metrics.disk_usage_percent > self.thresholds['disk_warning']):
                status = "warning"
                warnings = []
                if metrics.cpu_percent > self.thresholds['cpu_warning']:
                    warnings.append(f"CPU使用率较高: {metrics.cpu_percent:.1f}%")
                if metrics.memory_percent > self.thresholds['memory_warning']:
                    warnings.append(f"内存使用率较高: {metrics.memory_percent:.1f}%")
                if metrics.disk_usage_percent > self.thresholds['disk_warning']:
                    warnings.append(f"磁盘使用率较高: {metrics.disk_usage_percent:.1f}%")
                message = "; ".join(warnings)
            else:
                status = "healthy"
                message = "系统运行正常"
            
            health_status = HealthStatus(
                status=status,
                database=db_healthy,
                memory_ok=memory_ok,
                disk_ok=disk_ok,
                cpu_ok=cpu_ok,
                message=message,
                timestamp=datetime.now()
            )
            
            logger.info(f"健康检查完成: {status} - {message}")
            return health_status
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return HealthStatus(
                status="critical",
                database=False,
                memory_ok=False,
                disk_ok=False,
                cpu_ok=False,
                message=f"健康检查异常: {str(e)}",
                timestamp=datetime.now()
            )
    
    def get_uptime(self) -> timedelta:
        """获取系统运行时间"""
        return datetime.now() - self.start_time
    
    def get_metrics_summary(self, minutes: int = 10) -> Dict[str, Any]:
        """获取最近N分钟的指标汇总"""
        if not self.metrics_history:
            return {}
        
        # 筛选最近N分钟的数据
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        # 计算平均值和最大值
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        disk_values = [m.disk_usage_percent for m in recent_metrics]
        
        return {
            "time_range_minutes": minutes,
            "samples_count": len(recent_metrics),
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory": {
                "avg": sum(memory_values) / len(memory_values),
                "max": max(memory_values),
                "min": min(memory_values)
            },
            "disk": {
                "avg": sum(disk_values) / len(disk_values),
                "max": max(disk_values),
                "min": min(disk_values)
            }
        }


# 全局监控器实例
system_monitor = SystemMonitor()


async def start_monitoring_task():
    """启动后台监控任务"""
    logger.info("系统监控任务启动")
    
    while True:
        try:
            # 每5分钟收集一次指标
            await system_monitor.collect_system_metrics()
            
            # 每30分钟执行一次健康检查
            if datetime.now().minute % 30 == 0:
                health = await system_monitor.check_health()
                if health.status != "healthy":
                    logger.warning(f"系统健康状态异常: {health.message}")
            
            await asyncio.sleep(300)  # 5分钟
            
        except Exception as e:
            logger.error(f"监控任务异常: {e}")
            await asyncio.sleep(60)  # 出错后等待1分钟再重试
