import paramiko
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
import re
from config import Config
from states import ExecutionResult
from logger_config import get_logger, error_logger, log_operation, log_performance

logger = get_logger(__name__)

class RemoteExecutor:
    """远程服务器命令执行器"""

    def __init__(self, server_config: Dict = None):
        self.server_config = server_config or Config.get_server_config()
        self.ssh_client = None
        self.sftp_client = None

    @error_logger(context="SSH连接建立")
    def connect(self) -> bool:
        """建立SSH连接"""
        start_time = time.time()

        try:
            log_operation("开始建立SSH连接",
                         {"hostname": self.server_config["hostname"],
                          "port": self.server_config["port"],
                          "username": self.server_config["username"]},
                         user="remote_executor")

            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.ssh_client.connect(
                hostname=self.server_config["hostname"],
                port=self.server_config["port"],
                username=self.server_config["username"],
                password=self.server_config["password"],
                timeout=self.server_config["timeout"]
            )

            logger.info(f"成功连接到服务器 {self.server_config['hostname']}")
            return True

        except paramiko.AuthenticationException:
            logger.error("SSH认证失败")
            return False
        except paramiko.SSHException as e:
            logger.error(f"SSH连接错误: {e}")
            return False
        except Exception as e:
            logger.error(f"连接服务器失败: {e}")
            return False

    def disconnect(self):
        """断开SSH连接"""
        if self.sftp_client:
            self.sftp_client.close()
        if self.ssh_client:
            self.ssh_client.close()
        logger.info("已断开SSH连接")

    def execute_command(self, command: str, timeout: int = 30) -> ExecutionResult:
        """执行远程命令"""
        start_time = time.time()

        try:
            if not self.ssh_client:
                if not self.connect():
                    return ExecutionResult(
                        command=command,
                        success=False,
                        output="",
                        error="无法连接到服务器"
                    )

            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)

            output = stdout.read().decode('utf-8', errors='ignore').strip()
            error = stderr.read().decode('utf-8', errors='ignore').strip()
            exit_code = stdout.channel.recv_exit_status()

            execution_time = time.time() - start_time

            success = exit_code == 0

            result = ExecutionResult(
                command=command,
                success=success,
                output=output,
                error=error if error else None,
                execution_time=execution_time,
                timestamp=datetime.now()
            )

            logger.info(f"命令执行完成: {command} (耗时: {execution_time:.2f}s, 状态: {'成功' if success else '失败'})")
            return result

        except paramiko.SSHException as e:
            logger.error(f"SSH执行错误: {e}")
            return ExecutionResult(
                command=command,
                success=False,
                output="",
                error=f"SSH执行错误: {e}",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            return ExecutionResult(
                command=command,
                success=False,
                output="",
                error=f"执行失败: {e}",
                execution_time=time.time() - start_time
            )

    def execute_commands(self, commands: List[str], timeout: int = 30) -> List[ExecutionResult]:
        """批量执行命令"""
        results = []
        for command in commands:
            result = self.execute_command(command, timeout)
            results.append(result)

            # 如果命令执行失败，可以选择停止后续执行
            if not result.success:
                logger.warning(f"命令 '{command}' 执行失败，跳过后续命令")
                break

        return results

    def get_system_info(self) -> Dict[str, str]:
        """获取系统基本信息"""
        commands = {
            "hostname": "hostname",
            "os_release": "cat /etc/os-release",
            "kernel_version": "uname -r",
            "uptime": "uptime",
            "whoami": "whoami"
        }

        info = {}
        for key, command in commands.items():
            result = self.execute_command(command)
            if result.success:
                info[key] = result.output
            else:
                info[key] = "获取失败"

        return info

    def analyze_cpu_usage(self) -> Dict[str, any]:
        """分析CPU使用情况"""
        commands = [
            "top -bn1 | head -20",
            "ps aux --sort=-%cpu | head -10",
            "grep 'processor' /proc/cpuinfo | wc -l"
        ]

        results = self.execute_commands(commands)

        analysis = {
            "top_output": results[0].output if results[0].success else "",
            "high_cpu_processes": results[1].output if results[1].success else "",
            "cpu_cores": results[2].output if results[2].success else "0"
        }

        # 解析CPU核心数
        try:
            analysis["cpu_cores"] = int(analysis["cpu_cores"])
        except (ValueError, TypeError):
            analysis["cpu_cores"] = 1

        return analysis

    def analyze_memory_usage(self) -> Dict[str, str]:
        """分析内存使用情况"""
        commands = [
            "free -h",
            "ps aux --sort=-%mem | head -10",
            "cat /proc/meminfo | grep -E 'MemTotal|MemFree|MemAvailable|Cached|Buffers'"
        ]

        results = self.execute_commands(commands)

        return {
            "memory_info": results[0].output if results[0].success else "",
            "high_memory_processes": results[1].output if results[1].success else "",
            "memory_details": results[2].output if results[2].success else ""
        }

    def analyze_disk_usage(self) -> Dict[str, str]:
        """分析磁盘使用情况"""
        commands = [
            "df -h",
            "du -sh /* | sort -rh | head -10",
            "find /tmp -type f -size +100M -exec ls -lh {} \; 2>/dev/null"
        ]

        results = self.execute_commands(commands)

        return {
            "disk_usage": results[0].output if results[0].success else "",
            "large_directories": results[1].output if results[1].success else "",
            "large_temp_files": results[2].output if results[2].success else ""
        }

    def analyze_network_connections(self) -> Dict[str, str]:
        """分析网络连接情况"""
        commands = [
            "netstat -an | grep ESTABLISHED | wc -l",
            "ss -tuln | head -20",
            "netstat -tuln | head -20"
        ]

        results = self.execute_commands(commands)

        return {
            "connection_count": results[0].output if results[0].success else "0",
            "socket_status": results[1].output if results[1].success else "",
            "listening_ports": results[2].output if results[2].success else ""
        }

    def kill_process(self, pid: int, signal: int = 9) -> ExecutionResult:
        """终止进程"""
        command = f"kill -{signal} {pid}"
        return self.execute_command(command)

    def find_process_by_name(self, process_name: str) -> List[Dict[str, str]]:
        """根据进程名查找进程"""
        command = f"ps aux | grep '{process_name}' | grep -v grep"
        result = self.execute_command(command)

        processes = []
        if result.success:
            lines = result.output.split('\n')
            for line in lines:
                if line.strip():
                    # 解析ps输出格式
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        processes.append({
                            "user": parts[0],
                            "pid": parts[1],
                            "cpu": parts[2],
                            "mem": parts[3],
                            "command": parts[10]
                        })

        return processes

    def cleanup_temp_files(self) -> ExecutionResult:
        """清理临时文件"""
        command = "find /tmp -type f -atime +7 -delete && find /var/tmp -type f -atime +7 -delete"
        return self.execute_command(command)

    def clear_system_cache(self) -> ExecutionResult:
        """清理系统缓存"""
        command = "sync && echo 3 > /proc/sys/vm/drop_caches"
        return self.execute_command(command)

    def restart_service(self, service_name: str) -> ExecutionResult:
        """重启服务"""
        commands = [
            f"systemctl restart {service_name}",
            f"systemctl status {service_name}"
        ]
        results = self.execute_commands(commands)
        return results[-1]  # 返回状态检查结果

    def check_service_status(self, service_name: str) -> ExecutionResult:
        """检查服务状态"""
        command = f"systemctl status {service_name}"
        return self.execute_command(command)

    def get_service_logs(self, service_name: str, lines: int = 50) -> ExecutionResult:
        """获取服务日志"""
        command = f"journalctl -u {service_name} --no-pager -n {lines}"
        return self.execute_command(command)

    def monitor_real_time_metrics(self, duration: int = 60) -> Dict[str, str]:
        """实时监控系统指标"""
        commands = [
            "iostat -x 1 10",  # IO统计
            "sar -u 1 10",     # CPU使用率
            "sar -r 1 10",     # 内存使用率
            "sar -n DEV 1 5"   # 网络统计
        ]

        results = {}
        for i, command in enumerate(commands):
            result = self.execute_command(command, timeout=duration + 10)
            metric_type = ["io_stats", "cpu_stats", "memory_stats", "network_stats"][i]
            results[metric_type] = result.output if result.success else ""

        return results

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()