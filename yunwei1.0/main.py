#!/usr/bin/env python3
"""
智能运维助手主程序
基于LangGraph的智能Linux系统运维工具
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ops_graph import OpsAssistantGraph
from config import Config

# 配置日志
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ops_assistant.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class SmartOpsAssistant:
    """智能运维助手主类"""

    def __init__(self):
        self.ops_graph = OpsAssistantGraph()
        self.running = False

    def print_banner(self):
        """打印欢迎横幅"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                    智能运维助手 v1.0                          ║
║                Smart Operations Assistant                    ║
╚══════════════════════════════════════════════════════════════╝

基于LangGraph构建的智能Linux系统运维工具

功能特性:
🔍 智能监控分析 - 基于Prometheus和AI的系统监控
🤖 自动故障诊断 - 智能识别系统问题和异常
⚡ 自动修复执行 - 自动执行常见运维操作
📊 实时状态报告 - 生成详细的系统状态报告

配置信息:
📍 目标服务器: {server_host}
📊 Prometheus地址: {prometheus_url}
🤖 AI模型: {llm_model}
        """.format(
            server_host=Config.SERVER_HOST,
            prometheus_url=Config.PROMETHEUS_URL,
            llm_model=Config.LLM_MODEL
        )
        print(banner)

    def print_help(self):
        """打印帮助信息"""
        help_text = """
📋 可用命令:

check                - 执行完整的系统检查和分析
status               - 显示当前系统状态
metrics              - 显示监控指标详情
alerts               - 显示活跃告警
history              - 显示操作历史
config               - 显示配置信息
help                 - 显示此帮助信息
exit/quit            - 退出程序

💡 使用示例:
  > check            # 执行一次完整的智能运维检查
  > status           # 查看系统总体状态
  > help             # 显示帮助信息
        """
        print(help_text)

    async def handle_check_command(self) -> Dict[str, Any]:
        """处理检查命令"""
        print("🔍 开始执行智能运维检查...")
        print("⏳ 正在收集监控数据和分析系统状态...\n")

        result = await self.ops_graph.run()

        if result["success"]:
            print("✅ 智能运维检查完成!\n")
            print("=" * 60)
            print(result["response"])
            print("=" * 60)

            # 显示简要摘要
            summary = result["summary"]
            print(f"\n📊 检查摘要:\n{summary}")
        else:
            print(f"❌ 检查执行失败: {result.get('error', '未知错误')}")

        return result

    async def handle_status_command(self):
        """处理状态命令"""
        state = self.ops_graph.get_current_state()

        print("📊 当前系统状态:")
        print(f"   总体状态: {state['system_status'].value}")
        print(f"   监控指标: {len(state['metrics'])} 个")
        print(f"   活跃告警: {len(state['alerts'])} 个")

        if state['alerts']:
            critical_count = len([a for a in state['alerts'] if a.level.value == 'critical'])
            warning_count = len([a for a in state['alerts'] if a.level.value == 'warning'])
            print(f"   告警分布: 🔴 严重 {critical_count} 个, 🟡 警告 {warning_count} 个")

        if state['execution_plan']:
            print(f"   待执行操作: {len(state['execution_plan'])} 个")

        if state.get('error_message'):
            print(f"   ⚠️ 错误: {state['error_message']}")

    def handle_metrics_command(self):
        """处理指标命令"""
        state = self.ops_graph.get_current_state()
        metrics = state['metrics']

        if not metrics:
            print("📊 暂无监控数据，请先执行 'check' 命令")
            return

        print("📊 监控指标详情:")
        print("-" * 80)

        # 按类型分组显示
        cpu_metrics = [m for m in metrics if 'cpu' in m.name.lower()]
        memory_metrics = [m for m in metrics if 'memory' in m.name.lower()]
        disk_metrics = [m for m in metrics if 'disk' in m.name.lower()]
        network_metrics = [m for m in metrics if 'network' in m.name.lower() or 'tcp' in m.name.lower()]

        def show_metrics(metrics_list, title):
            if metrics_list:
                print(f"\n🔹 {title}:")
                for metric in metrics_list:
                    status_icon = "❌" if metric.status.value == 'critical' else "⚠️" if metric.status.value == 'warning' else "✅"
                    threshold_info = f" (阈值: {metric.threshold})" if metric.threshold else ""
                    print(f"   {status_icon} {metric.name}: {metric.value:.2f}{metric.unit}{threshold_info}")

        show_metrics(cpu_metrics, "CPU指标")
        show_metrics(memory_metrics, "内存指标")
        show_metrics(disk_metrics, "磁盘指标")
        show_metrics(network_metrics, "网络指标")

        print("-" * 80)

    def handle_alerts_command(self):
        """处理告警命令"""
        state = self.ops_graph.get_current_state()
        alerts = state['alerts']

        if not alerts:
            print("🚨 暂无活跃告警")
            return

        print(f"🚨 活跃告警 ({len(alerts)} 个):")
        print("-" * 80)

        for i, alert in enumerate(alerts, 1):
            level_icon = "🔴" if alert.level.value == 'critical' else "🟡"
            print(f"{i}. {level_icon} **{alert.metric_name}**")
            print(f"   📝 消息: {alert.message}")
            print(f"   📊 当前值: {alert.value}, 阈值: {alert.threshold}")
            print(f"   ⏰ 时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            if alert.suggested_actions:
                print(f"   💡 建议操作:")
                for action in alert.suggested_actions:
                    print(f"      • {action}")
            print()

        print("-" * 80)

    def handle_history_command(self):
        """处理历史命令"""
        state = self.ops_graph.get_current_state()
        history = state['action_history']
        conversation = state['conversation_history']

        print("📜 操作历史:")
        print("-" * 80)

        if history:
            print("🔧 系统操作:")
            for i, action in enumerate(history[-10:], 1):  # 显示最近10条
                timestamp = action.get('timestamp', '未知时间')
                action_type = action.get('type', '未知操作')
                print(f"   {i}. [{timestamp}] {action_type}")

        if conversation:
            print(f"\n💬 对话记录 ({len(conversation)} 条):")
            for i, conv in enumerate(conversation[-5:], 1):  # 显示最近5条
                timestamp = conv.get('timestamp', '未知时间')
                user_msg = conv.get('user', '未知')[:50] + "..." if len(conv.get('user', '')) > 50 else conv.get('user', '未知')
                print(f"   {i}. [{timestamp}] 用户: {user_msg}")

        if not history and not conversation:
            print("   暂无操作记录")

        print("-" * 80)

    def handle_config_command(self):
        """处理配置命令"""
        print("⚙️ 当前配置:")
        print("-" * 80)
        print(f"🖥️  目标服务器: {Config.SERVER_HOST}:{Config.SERVER_PORT}")
        print(f"👤 登录用户: {Config.SERVER_USER}")
        print(f"📊 Prometheus地址: {Config.PROMETHEUS_URL}")
        print(f"🤖 AI模型: {Config.LLM_MODEL}")
        print(f"🔗 LLM地址: {Config.LLM_BASE_URL}")

        print(f"\n📊 阈值配置:")
        print(f"   CPU使用率阈值: {Config.THRESHOLDS['cpu_usage']}%")
        print(f"   内存使用率阈值: {Config.THRESHOLDS['memory_usage']}%")
        print(f"   磁盘使用率阈值: {Config.THRESHOLDS['disk_usage']}%")
        print(f"   系统负载阈值: {Config.THRESHOLDS['load_average']}")
        print(f"   连接数阈值: {Config.THRESHOLDS['connection_count']}")

        print("-" * 80)

    async def run_interactive_mode(self):
        """运行交互模式"""
        self.print_banner()
        print("\n输入 'help' 查看可用命令，输入 'exit' 退出程序\n")

        self.running = True

        while self.running:
            try:
                command = input("智能运维助手 > ").strip().lower()

                if not command:
                    continue

                if command in ['exit', 'quit']:
                    print("👋 感谢使用智能运维助手，再见!")
                    self.running = False

                elif command == 'help':
                    self.print_help()

                elif command == 'check':
                    await self.handle_check_command()

                elif command == 'status':
                    self.handle_status_command()

                elif command == 'metrics':
                    self.handle_metrics_command()

                elif command == 'alerts':
                    self.handle_alerts_command()

                elif command == 'history':
                    self.handle_history_command()

                elif command == 'config':
                    self.handle_config_command()

                else:
                    print(f"❌ 未知命令: '{command}'")
                    print("💡 输入 'help' 查看可用命令")

                print()  # 添加空行

            except KeyboardInterrupt:
                print("\n👋 程序被中断，再见!")
                self.running = False

            except Exception as e:
                print(f"❌ 命令执行出错: {e}")

    async def run_single_check(self):
        """运行单次检查模式"""
        print("🚀 启动智能运维助手 (单次检查模式)")
        print("-" * 60)

        result = await self.handle_check_command()

        if not result["success"]:
            sys.exit(1)

async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="智能运维助手")
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='启动交互模式')
    parser.add_argument('--check', '-c', action='store_true',
                       help='执行单次系统检查')
    parser.add_argument('--version', '-v', action='version', version='%(prog)s 1.0')

    args = parser.parse_args()

    # 如果没有参数，默认启动交互模式
    if not args.interactive and not args.check:
        args.interactive = True

    try:
        assistant = SmartOpsAssistant()

        if args.interactive:
            await assistant.run_interactive_mode()
        elif args.check:
            await assistant.run_single_check()

    except Exception as e:
        logger.error(f"程序运行失败: {e}")
        print(f"❌ 程序运行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())