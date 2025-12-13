import requests
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from config import Config
from states import MetricValue, SystemAlert, AlertLevel
from logger_config import get_logger, error_logger, log_operation, log_performance

logger = get_logger(__name__)

class PrometheusClient:
    """Prometheus监控数据客户端"""

    def __init__(self, prometheus_url: str = None):
        self.prometheus_url = prometheus_url or Config.PROMETHEUS_URL
        self.session = requests.Session()
        self.session.timeout = Config.TIMEOUT

    @error_logger(context="Prometheus数据获取")
    def fetch_metrics(self) -> List[MetricValue]:
        """从Prometheus获取监控指标"""
        import time
        start_time = time.time()

        try:
            log_operation("开始获取Prometheus指标",
                        {"prometheus_url": self.prometheus_url})

            response = self.session.get(self.prometheus_url)
            response.raise_for_status()

            metrics_text = response.text
            metrics = self._parse_metrics(metrics_text)

            end_time = time.time()
            log_performance("fetch_metrics", start_time, end_time,
                          {"metrics_count": len(metrics)})

            log_operation("成功获取Prometheus指标",
                        {"metrics_count": len(metrics)})

            return metrics

        except requests.RequestException as e:
            logger.error(f"获取Prometheus指标失败: {e}")
            log_operation("获取Prometheus指标失败",
                        {"error": str(e), "url": self.prometheus_url},
                        level="error")
            raise Exception(f"无法连接到Prometheus: {e}")

    def _parse_metrics(self, metrics_text: str) -> List[MetricValue]:
        """解析Prometheus指标格式"""
        metrics = []
        timestamp = datetime.now()

        # 定义关键指标的解析规则
        metric_patterns = {
            # CPU相关指标
            'cpu_usage': r'node_cpu_seconds_total{cpu="0",mode="idle"}\s+([\d.]+)',
            'load_1m': r'node_load1\s+([\d.]+)',
            'load_5m': r'node_load5\s+([\d.]+)',
            'load_15m': r'node_load15\s+([\d.]+)',

            # 内存相关指标
            'memory_total': r'node_memory_MemTotal_bytes\s+([\d.]+)',
            'memory_available': r'node_memory_MemAvailable_bytes\s+([\d.]+)',
            'memory_cached': r'node_memory_Cached_bytes\s+([\d.]+)',
            'memory_buffers': r'node_memory_Buffers_bytes\s+([\d.]+)',
            'memory_free': r'node_memory_MemFree_bytes\s+([\d.]+)',

            # 磁盘相关指标
            'disk_total': r'node_filesystem_size_bytes{fstype!="rootfs"}\s+([\d.]+)',
            'disk_free': r'node_filesystem_free_bytes{fstype!="rootfs"}\s+([\d.]+)',
            'disk_used': r'node_filesystem_size_bytes{fstype!="rootfs"} - node_filesystem_free_bytes{fstype!="rootfs"}',

            # 网络相关指标
            'network_receive_bytes': r'node_network_receive_bytes_total\s+([\d.]+)',
            'network_transmit_bytes': r'node_network_transmit_bytes_total\s+([\d.]+)',

            # 连接数
            'tcp_connections': r'node_netstat_Tcp_CurrEstab\s+([\d.]+)',
        }

        # 解析基础指标
        raw_metrics = {}
        for metric_name, pattern in metric_patterns.items():
            match = re.search(pattern, metrics_text)
            if match:
                raw_metrics[metric_name] = float(match.group(1))

        # 计算衍生指标
        metrics.extend(self._calculate_cpu_metrics(raw_metrics, timestamp))
        metrics.extend(self._calculate_memory_metrics(raw_metrics, timestamp))
        metrics.extend(self._calculate_disk_metrics(raw_metrics, timestamp))
        metrics.extend(self._calculate_network_metrics(raw_metrics, timestamp))
        metrics.extend(self._calculate_system_metrics(raw_metrics, timestamp))

        return metrics

    def _calculate_cpu_metrics(self, raw_metrics: Dict[str, float], timestamp: datetime) -> List[MetricValue]:
        """计算CPU相关指标"""
        metrics = []

        # CPU空闲率
        if 'cpu_usage' in raw_metrics:
            # 这里简化处理，实际应该计算时间差
            idle_percent = raw_metrics['cpu_usage'] * 100
            cpu_usage = max(0, 100 - idle_percent)  # 确保不为负数

            metrics.append(MetricValue(
                name="cpu_usage_percent",
                value=cpu_usage,
                unit="percent",
                timestamp=timestamp,
                threshold=Config.THRESHOLDS["cpu_usage"],
                status=AlertLevel.WARNING if cpu_usage > Config.THRESHOLDS["cpu_usage"] else AlertLevel.NORMAL
            ))

        # 负载均衡指标
        for load_type, load_name in [('load_1m', 'load_1m'), ('load_5m', 'load_5m'), ('load_15m', 'load_15m')]:
            if load_type in raw_metrics:
                load_value = raw_metrics[load_type]
                metrics.append(MetricValue(
                    name=load_name,
                    value=load_value,
                    unit="load",
                    timestamp=timestamp,
                    threshold=Config.THRESHOLDS["load_average"],
                    status=AlertLevel.WARNING if load_value > Config.THRESHOLDS["load_average"] else AlertLevel.NORMAL
                ))

        return metrics

    def _calculate_memory_metrics(self, raw_metrics: Dict[str, float], timestamp: datetime) -> List[MetricValue]:
        """计算内存相关指标"""
        metrics = []

        if 'memory_total' in raw_metrics and 'memory_available' in raw_metrics:
            total = raw_metrics['memory_total']
            available = raw_metrics['memory_available']

            if total > 0:
                used = total - available
                usage_percent = (used / total) * 100

                # 原始字节数指标
                metrics.append(MetricValue(
                    name="memory_total_bytes",
                    value=total,
                    unit="bytes",
                    timestamp=timestamp
                ))

                metrics.append(MetricValue(
                    name="memory_used_bytes",
                    value=used,
                    unit="bytes",
                    timestamp=timestamp
                ))

                metrics.append(MetricValue(
                    name="memory_available_bytes",
                    value=available,
                    unit="bytes",
                    timestamp=timestamp
                ))

                # 使用率指标
                metrics.append(MetricValue(
                    name="memory_usage_percent",
                    value=usage_percent,
                    unit="percent",
                    timestamp=timestamp,
                    threshold=Config.THRESHOLDS["memory_usage"],
                    status=AlertLevel.WARNING if usage_percent > Config.THRESHOLDS["memory_usage"] else AlertLevel.NORMAL
                ))

        return metrics

    def _calculate_disk_metrics(self, raw_metrics: Dict[str, float], timestamp: datetime) -> List[MetricValue]:
        """计算磁盘相关指标"""
        metrics = []

        # 简化处理：假设第一个磁盘分区
        disk_keys = [k for k in raw_metrics.keys() if k.startswith('disk_total')]
        for key in disk_keys:
            total_key = key
            free_key = key.replace('total', 'free')

            if total_key in raw_metrics and free_key in raw_metrics:
                total = raw_metrics[total_key]
                free = raw_metrics[free_key]

                if total > 0:
                    used = total - free
                    usage_percent = (used / total) * 100

                    metrics.append(MetricValue(
                        name=f"disk_usage_percent",
                        value=usage_percent,
                        unit="percent",
                        timestamp=timestamp,
                        threshold=Config.THRESHOLDS["disk_usage"],
                        status=AlertLevel.WARNING if usage_percent > Config.THRESHOLDS["disk_usage"] else AlertLevel.NORMAL
                    ))

                    metrics.append(MetricValue(
                        name=f"disk_used_gb",
                        value=used / (1024**3),
                        unit="GB",
                        timestamp=timestamp
                    ))

                    metrics.append(MetricValue(
                        name=f"disk_total_gb",
                        value=total / (1024**3),
                        unit="GB",
                        timestamp=timestamp
                    ))
                break  # 只处理第一个磁盘分区

        return metrics

    def _calculate_network_metrics(self, raw_metrics: Dict[str, float], timestamp: datetime) -> List[MetricValue]:
        """计算网络相关指标"""
        metrics = []

        # TCP连接数
        if 'tcp_connections' in raw_metrics:
            connections = raw_metrics['tcp_connections']
            metrics.append(MetricValue(
                name="tcp_connections",
                value=connections,
                unit="count",
                timestamp=timestamp,
                threshold=Config.THRESHOLDS["connection_count"],
                status=AlertLevel.WARNING if connections > Config.THRESHOLDS["connection_count"] else AlertLevel.NORMAL
            ))

        return metrics

    def _calculate_system_metrics(self, raw_metrics: Dict[str, float], timestamp: datetime) -> List[MetricValue]:
        """计算系统级指标"""
        metrics = []

        # 系统运行时间（如果有uptime指标）
        uptime_pattern = r'node_boot_time_seconds\s+([\d.]+)'
        # 这里可以添加更多系统指标的计算逻辑

        return metrics

    def detect_alerts(self, metrics: List[MetricValue]) -> List[SystemAlert]:
        """基于指标检测告警"""
        alerts = []

        for metric in metrics:
            if metric.threshold and metric.value > metric.threshold:
                alert_level = AlertLevel.CRITICAL if metric.value > metric.threshold * 1.2 else AlertLevel.WARNING

                alert = SystemAlert(
                    metric_name=metric.name,
                    level=alert_level,
                    message=self._generate_alert_message(metric),
                    value=metric.value,
                    threshold=metric.threshold,
                    timestamp=metric.timestamp,
                    suggested_actions=self._get_suggested_actions(metric.name)
                )
                alerts.append(alert)

        return alerts

    def _generate_alert_message(self, metric: MetricValue) -> str:
        """生成告警消息"""
        messages = {
            "cpu_usage_percent": f"CPU使用率过高: {metric.value:.1f}%",
            "memory_usage_percent": f"内存使用率过高: {metric.value:.1f}%",
            "disk_usage_percent": f"磁盘使用率过高: {metric.value:.1f}%",
            "load_1m": f"系统负载过高: {metric.value:.2f}",
            "tcp_connections": f"TCP连接数过多: {int(metric.value)}"
        }

        return messages.get(metric.name, f"指标 {metric.name} 异常: {metric.value}")

    def _get_suggested_actions(self, metric_name: str) -> List[str]:
        """获取建议的修复操作"""
        actions = {
            "cpu_usage_percent": [
                "检查CPU占用高的进程",
                "考虑终止非必要进程",
                "检查系统是否有异常计算任务"
            ],
            "memory_usage_percent": [
                "检查内存占用高的进程",
                "清理系统缓存",
                "考虑重启内存泄露的服务"
            ],
            "disk_usage_percent": [
                "清理临时文件",
                "删除不必要的日志文件",
                "检查大文件并清理"
            ],
            "load_1m": [
                "检查系统负载高的原因",
                "查看运行中的进程",
                "考虑优化系统配置"
            ],
            "tcp_connections": [
                "检查网络连接状态",
                "查看是否有异常连接",
                "考虑调整网络参数"
            ]
        }

        return actions.get(metric_name, ["检查系统状态", "联系系统管理员"])