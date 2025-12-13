#!/usr/bin/env python3
"""
智能运维助手使用示例
演示如何在不同场景下使用智能运维助手
"""

import asyncio
import logging
from datetime import datetime

from ops_graph import OpsAssistantGraph
from monitoring import PrometheusClient
from remote_executor import RemoteExecutor
from analyzer import SystemAnalyzer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def example_basic_check():
    """示例1: 基础系统检查"""
    print("=" * 60)
    print("示例1: 执行基础系统检查")
    print("=" * 60)

    assistant = OpsAssistantGraph()
    result = await assistant.run("执行一次完整的系统健康检查")

    if result["success"]:
        print("✅ 系统检查完成")
        print("📊 检查结果摘要:")
        print(result["summary"])
        print("\n📋 详细报告:")
        print(result["response"])
    else:
        print(f"❌ 系统检查失败: {result.get('error')}")

async def example_monitoring_only():
    """示例2: 仅获取监控数据"""
    print("\n" + "=" * 60)
    print("示例2: 获取Prometheus监控数据")
    print("=" * 60)

    prometheus = PrometheusClient()

    try:
        metrics = prometheus.fetch_metrics()
        alerts = prometheus.detect_alerts(metrics)

        print(f"📊 获取到 {len(metrics)} 个监控指标")
        print(f"🚨 检测到 {len(alerts)} 个告警")

        # 显示关键指标
        critical_metrics = [m for m in metrics if m.status.value in ['warning', 'critical']]
        if critical_metrics:
            print("\n⚠️ 异常指标:")
            for metric in critical_metrics[:5]:
                print(f"  - {metric.name}: {metric.value}{metric.unit}")

        # 显示告警
        if alerts:
            print("\n🚨 活跃告警:")
            for alert in alerts[:3]:
                print(f"  - {alert.metric_name}: {alert.message}")

    except Exception as e:
        print(f"❌ 获取监控数据失败: {e}")

async def example_remote_commands():
    """示例3: 执行远程命令"""
    print("\n" + "=" * 60)
    print("示例3: 执行远程运维命令")
    print("=" * 60)

    with RemoteExecutor() as executor:
        try:
            print("🔍 获取系统基本信息...")
            system_info = executor.get_system_info()

            for key, value in system_info.items():
                print(f"  {key}: {value}")

            print("\n📊 分析CPU使用情况...")
            cpu_analysis = executor.analyze_cpu_usage()
            print(f"  CPU核心数: {cpu_analysis['cpu_cores']}")
            print(f"  高CPU进程前10名:\n{cpu_analysis['high_cpu_processes']}")

            print("\n💾 分析内存使用情况...")
            memory_analysis = executor.analyze_memory_usage()
            print(f"  内存信息:\n{memory_analysis['memory_info']}")

        except Exception as e:
            print(f"❌ 远程命令执行失败: {e}")

async def example_ai_analysis():
    """示例4: AI智能分析"""
    print("\n" + "=" * 60)
    print("示例4: AI智能系统分析")
    print("=" * 60)

    prometheus = PrometheusClient()
    analyzer = SystemAnalyzer()

    try:
        # 获取监控数据
        metrics = prometheus.fetch_metrics()
        alerts = prometheus.detect_alerts(metrics)

        print(f"📊 准备分析 {len(metrics)} 个指标和 {len(alerts)} 个告警...")

        # AI分析
        analysis_result = analyzer.analyze_metrics(metrics, alerts)

        print("\n🤖 AI分析结果:")
        print(f"  检测到问题: {len(analysis_result['detected_issues'])} 个")
        print(f"  建议操作: {len(analysis_result['recommended_actions'])} 个")
        print(f"  紧急程度: {analysis_result['urgency']}")
        print(f"  可自动修复: {analysis_result['auto_fixable']}")

        print("\n📋 检测到的问题:")
        for issue in analysis_result['detected_issues']:
            print(f"  - {issue}")

        print("\n💡 建议操作:")
        for action in analysis_result['recommended_actions']:
            print(f"  - {action}")

        # 生成执行计划
        execution_plan = analyzer.generate_execution_plan(analysis_result)
        if execution_plan:
            print(f"\n⚡ 自动执行计划 ({len(execution_plan)} 个操作):")
            for i, command in enumerate(execution_plan, 1):
                print(f"  {i}. {command}")
        else:
            print("\n⚡ 无需自动执行操作")

    except Exception as e:
        print(f"❌ AI分析失败: {e}")

async def example_custom_workflow():
    """示例5: 自定义工作流程"""
    print("\n" + "=" * 60)
    print("示例5: 自定义运维工作流程")
    print("=" * 60)

    prometheus = PrometheusClient()
    analyzer = SystemAnalyzer()
    executor = RemoteExecutor()

    try:
        print("🔄 步骤1: 收集监控数据...")
        metrics = prometheus.fetch_metrics()
        alerts = prometheus.detect_alerts(metrics)

        print("🤖 步骤2: AI分析...")
        analysis_result = analyzer.analyze_metrics(metrics, alerts)

        print("⚡ 步骤3: 生成执行计划...")
        execution_plan = analyzer.generate_execution_plan(analysis_result)

        if execution_plan and analysis_result.get('auto_fixable', False):
            print("🔧 步骤4: 执行自动修复...")
            with executor:
                results = executor.execute_commands(execution_plan)

            print("📊 步骤5: 分析执行结果...")
            success_count = len([r for r in results if r.success])
            print(f"  成功执行: {success_count}/{len(results)} 个命令")

            for result in results:
                status = "✅" if result.success else "❌"
                print(f"  {status} {result.command}")
                if result.error:
                    print(f"    错误: {result.error}")
        else:
            print("⏭️ 步骤4: 跳过自动执行 (无需修复或未启用自动修复)")

        print("📋 步骤6: 生成最终报告...")
        final_report = f"""
自定义工作流程执行报告:

执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
监控指标: {len(metrics)} 个
检测告警: {len(alerts)} 个
AI问题: {len(analysis_result['detected_issues'])} 个
执行计划: {len(execution_plan)} 个操作

系统状态评估: {analysis_result.get('overall_status', 'unknown')}
紧急程度: {analysis_result.get('urgency', 'medium')}
        """
        print(final_report)

    except Exception as e:
        print(f"❌ 自定义工作流程执行失败: {e}")

async def main():
    """主函数 - 运行所有示例"""
    print("🚀 智能运维助手使用示例")
    print("⚠️ 请确保已正确配置.env文件中的API密钥和服务器信息")

    try:
        # 运行所有示例
        await example_basic_check()
        await example_monitoring_only()
        await example_remote_commands()
        await example_ai_analysis()
        await example_custom_workflow()

        print("\n" + "=" * 60)
        print("✅ 所有示例执行完成!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n👋 示例执行被中断")
    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())