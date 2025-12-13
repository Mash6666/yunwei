import os
from typing import Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """智能运维助手配置类"""

    # LLM配置
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen-max")

    # 数据库配置
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
    DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")

    # Prometheus配置
    PROMETHEUS_URL = "http://10.0.0.81:9100/metrics"

    # 服务器连接配置
    SERVER_HOST = "10.0.0.81"
    SERVER_USER = "root"
    SERVER_PASSWORD = "178379733Mash"
    SERVER_PORT = 22

    # 运维助手配置
    MAX_RETRIES = 3
    TIMEOUT = 30
    LOG_LEVEL = "INFO"

    # 监控指标阈值
    THRESHOLDS = {
        "cpu_usage": 80.0,  # CPU使用率阈值(%)
        "memory_usage": 85.0,  # 内存使用率阈值(%)
        "disk_usage": 90.0,  # 磁盘使用率阈值(%)
        "load_average": 2.0,  # 负载均衡阈值
        "connection_count": 1000,  # 连接数阈值
    }

    # 自动修复策略
    AUTO_FIX_STRATEGIES = {
        "high_cpu": [
            "top -bn1 | head -20",
            "ps aux --sort=-%cpu | head -10",
            "kill -9 {pid}"  # 需要动态替换PID
        ],
        "high_memory": [
            "free -h",
            "ps aux --sort=-%mem | head -10",
            "sync && echo 3 > /proc/sys/vm/drop_caches"
        ],
        "high_disk": [
            "df -h",
            "du -sh /* | sort -rh | head -10",
            "find /tmp -type f -atime +7 -delete"
        ],
        "high_connections": [
            "netstat -an | grep ESTABLISHED | wc -l",
            "ss -tuln",
            "iptables -L"
        ]
    }

    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """获取LLM配置"""
        return {
            "api_key": cls.DASHSCOPE_API_KEY,
            "base_url": cls.LLM_BASE_URL,
            "model_name": cls.LLM_MODEL,
            "temperature": 0.1,
            "max_tokens": 2000
        }

    @classmethod
    def get_server_config(cls) -> Dict[str, Any]:
        """获取服务器连接配置"""
        return {
            "hostname": cls.SERVER_HOST,
            "port": cls.SERVER_PORT,
            "username": cls.SERVER_USER,
            "password": cls.SERVER_PASSWORD,
            "timeout": cls.TIMEOUT
        }

    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """获取数据库配置"""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
            "charset": cls.DB_CHARSET
        }