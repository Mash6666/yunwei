from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from states import OpsAssistantState, StateManager, SystemStatus
from monitoring import PrometheusClient
from remote_executor import RemoteExecutor
from analyzer import SystemAnalyzer

logger = logging.getLogger(__name__)

class OpsAssistantGraph:
    """智能运维助手工作流图"""

    def __init__(self):
        self.state_manager = StateManager()
        self.prometheus_client = PrometheusClient()
        self.system_analyzer = SystemAnalyzer()
        self.remote_executor = RemoteExecutor()

        # 创建工作流图
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建LangGraph工作流"""
        workflow = StateGraph(OpsAssistantState)

        # 添加节点
        workflow.add_node("collect_metrics", self._collect_metrics)
        workflow.add_node("analyze_system", self._analyze_system)
        workflow.add_node("generate_plan", self._generate_plan)
        workflow.add_node("execute_plan", self._execute_plan)
        workflow.add_node("report_results", self._report_results)
        workflow.add_node("handle_errors", self._handle_errors)

        # 设置入口点
        workflow.set_entry_point("collect_metrics")

        # 添加条件边
        workflow.add_conditional_edges(
            "collect_metrics",
            self._check_metrics_success,
            {
                "success": "analyze_system",
                "error": "handle_errors"
            }
        )

        workflow.add_conditional_edges(
            "analyze_system",
            self._check_analysis_result,
            {
                "needs_action": "generate_plan",
                "healthy": "report_results",
                "error": "handle_errors"
            }
        )

        workflow.add_conditional_edges(
            "generate_plan",
            self._check_plan_executable,
            {
                "execute": "execute_plan",
                "skip_execution": "report_results"
            }
        )

        workflow.add_edge("execute_plan", "report_results")
        workflow.add_edge("handle_errors", "report_results")
        workflow.add_edge("report_results", END)

        # 创建checkpointer
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    async def _collect_metrics(self, state: OpsAssistantState) -> OpsAssistantState:
        """收集监控指标"""
        try:
            logger.info("开始收集监控指标...")

            # 获取Prometheus指标
            metrics = self.prometheus_client.fetch_metrics()

            # 检测告警
            alerts = self.prometheus_client.detect_alerts(metrics)

            # 更新状态
            self.state_manager.update_metrics(metrics)
            for alert in alerts:
                self.state_manager.add_alert(alert)

            # 记录操作
            self.state_manager.add_action("collect_metrics", {
                "metrics_count": len(metrics),
                "alerts_count": len(alerts),
                "timestamp": datetime.now().isoformat()
            })

            logger.info(f"收集到 {len(metrics)} 个指标，{len(alerts)} 个告警")
            return self.state_manager.get_state()

        except Exception as e:
            logger.error(f"收集监控指标失败: {e}")
            state["error_message"] = f"监控数据收集失败: {str(e)}"
            return state

    async def _analyze_system(self, state: OpsAssistantState) -> OpsAssistantState:
        """分析系统状态"""
        try:
            logger.info("开始分析系统状态...")

            metrics = state["metrics"]
            alerts = state["alerts"]

            # 使用LLM进行智能分析
            analysis_result = self.system_analyzer.analyze_metrics(metrics, alerts)

            # 解析JSON格式的分析结果
            parsed_result = self.system_analyzer._parse_analysis_result(analysis_result["raw_analysis"])

            # 更新分析结果
            self.state_manager.update_analysis(
                analysis_result["raw_analysis"],
                parsed_result.get("issues", []),
                parsed_result
            )

            # 如果有修复计划，保存到状态中
            if "fix_plans" in parsed_result:
                self.state_manager.set_fix_plans(parsed_result["fix_plans"])

            # 记录操作
            self.state_manager.add_action("analyze_system", {
                "analysis_urgency": parsed_result.get("urgency", "medium"),
                "auto_fixable": parsed_result.get("auto_fixable", False),
                "issues_count": len(parsed_result.get("issues", [])),
                "fix_plans_count": len(parsed_result.get("fix_plans", [])),
                "timestamp": datetime.now().isoformat()
            })

            # 保存分析数据到上下文
            state["context"]["analysis_result"] = parsed_result

            logger.info(f"系统分析完成，检测到 {len(parsed_result.get('issues', []))} 个问题，{len(parsed_result.get('fix_plans', []))} 个修复计划")
            return self.state_manager.get_state()

        except Exception as e:
            logger.error(f"系统分析失败: {e}")
            state["error_message"] = f"系统分析失败: {str(e)}"
            return state

    async def _generate_plan(self, state: OpsAssistantState) -> OpsAssistantState:
        """生成执行计划"""
        try:
            logger.info("开始生成执行计划...")

            analysis_result = state["context"].get("analysis_result", {})

            if not analysis_result:
                state["error_message"] = "缺少分析结果，无法生成执行计划"
                return state

            # 生成执行计划
            execution_plan = self.system_analyzer.generate_execution_plan(analysis_result)

            # 更新状态
            self.state_manager.set_execution_plan(execution_plan)

            # 记录操作
            self.state_manager.add_action("generate_plan", {
                "plan_commands": len(execution_plan),
                "auto_fix_recommended": analysis_result.get("auto_fixable", False),
                "urgency": analysis_result.get("urgency", "medium"),
                "timestamp": datetime.now().isoformat()
            })

            logger.info(f"生成执行计划，包含 {len(execution_plan)} 个操作")
            return self.state_manager.get_state()

        except Exception as e:
            logger.error(f"生成执行计划失败: {e}")
            state["error_message"] = f"执行计划生成失败: {str(e)}"
            return state

    async def _execute_plan(self, state: OpsAssistantState) -> OpsAssistantState:
        """执行计划"""
        try:
            logger.info("开始执行运维计划...")

            execution_plan = state["execution_plan"]

            if not execution_plan:
                logger.info("没有需要执行的操作")
                return state

            # 连接到远程服务器
            with self.remote_executor as executor:
                for i, command in enumerate(execution_plan):
                    logger.info(f"执行操作 {i+1}/{len(execution_plan)}: {command}")

                    # 执行命令
                    result = executor.execute_command(command)

                    # 记录结果
                    self.state_manager.add_execution_result(result)

                    # 如果执行失败，记录错误但继续执行其他命令
                    if not result.success:
                        logger.warning(f"命令执行失败: {command}, 错误: {result.error}")

            # 记录操作
            self.state_manager.add_action("execute_plan", {
                "commands_executed": len(execution_plan),
                "success_count": len([r for r in state["execution_results"] if r.success]),
                "timestamp": datetime.now().isoformat()
            })

            logger.info(f"执行计划完成，共执行 {len(execution_plan)} 个操作")
            return self.state_manager.get_state()

        except Exception as e:
            logger.error(f"执行计划失败: {e}")
            state["error_message"] = f"计划执行失败: {str(e)}"
            return state

    async def _report_results(self, state: OpsAssistantState) -> OpsAssistantState:
        """报告结果"""
        try:
            logger.info("生成运维报告...")

            # 生成综合报告
            report = self._generate_report(state)

            # 更新AI响应
            state["ai_response"] = report

            # 记录操作
            self.state_manager.add_action("report_results", {
                "report_length": len(report),
                "system_status": state["system_status"].value,
                "timestamp": datetime.now().isoformat()
            })

            logger.info("运维报告生成完成")
            return state

        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            state["error_message"] = f"报告生成失败: {str(e)}"
            return state

    async def _handle_errors(self, state: OpsAssistantState) -> OpsAssistantState:
        """处理错误"""
        error_message = state.get("error_message", "未知错误")
        logger.error(f"处理错误: {error_message}")

        # 更新系统状态
        state["system_status"] = SystemStatus.CRITICAL

        # 生成错误报告
        error_report = f"""
## 错误报告

**错误信息**: {error_message}
**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**建议操作**:
1. 检查系统连接状态
2. 验证配置参数
3. 查看详细日志
4. 手动检查系统状态

**系统状态**: 严重异常，需要人工干预
"""

        state["ai_response"] = error_report

        # 记录错误操作
        self.state_manager.add_action("handle_errors", {
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        })

        return state

    def _check_metrics_success(self, state: OpsAssistantState) -> str:
        """检查指标收集是否成功"""
        if state.get("error_message"):
            return "error"

        if not state["metrics"]:
            return "error"

        return "success"

    def _check_analysis_result(self, state: OpsAssistantState) -> str:
        """检查分析结果"""
        if state.get("error_message"):
            return "error"

        analysis_result = state["context"].get("analysis_result", {})

        if not analysis_result:
            return "error"

        # 如果有检测到问题，需要执行操作
        if analysis_result.get("detected_issues"):
            return "needs_action"

        # 如果系统健康，直接报告
        return "healthy"

    def _check_plan_executable(self, state: OpsAssistantState) -> str:
        """检查是否需要执行计划"""
        if not state["execution_plan"]:
            return "skip_execution"

        analysis_result = state["context"].get("analysis_result", {})

        # 如果分析建议自动修复，则执行
        if analysis_result.get("auto_fixable", False):
            return "execute"

        # 如果有严重问题，也执行
        urgency = analysis_result.get("urgency", "low")
        if urgency in ["high", "critical"]:
            return "execute"

        # 否则跳过执行，只报告
        return "skip_execution"

    def _generate_report(self, state: OpsAssistantState) -> str:
        """生成运维报告"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        report = f"""
# 智能运维助手报告

**生成时间**: {timestamp}
**会话ID**: {state['session_id']}

## 系统状态概览
**总体状态**: {state['system_status'].value}
**监控指标数量**: {len(state['metrics'])}
**活跃告警数量**: {len(state['alerts'])}

## 关键指标
"""

        # 添加关键指标信息
        critical_metrics = [m for m in state['metrics'] if m.status.value in ['warning', 'critical']]
        if critical_metrics:
            report += "\n### 异常指标\n"
            for metric in critical_metrics[:5]:  # 只显示前5个异常指标
                status_icon = "❌" if metric.status.value == 'critical' else "⚠️"
                report += f"- {status_icon} **{metric.name}**: {metric.value}{metric.unit}"
                if metric.threshold:
                    report += f" (阈值: {metric.threshold})"
                report += "\n"

        # 添加告警信息
        if state['alerts']:
            report += "\n## 活跃告警\n"
            for alert in state['alerts'][:3]:  # 只显示前3个告警
                level_icon = "🔴" if alert.level.value == 'critical' else "🟡"
                report += f"- {level_icon} **{alert.metric_name}**: {alert.message}\n"
                report += f"  - 当前值: {alert.value}, 阈值: {alert.threshold}\n"
                if alert.suggested_actions:
                    report += f"  - 建议操作: {', '.join(alert.suggested_actions[:2])}\n"

        # 添加分析结果
        if state.get('analysis_result'):
            report += "\n## 智能分析结果\n"
            report += state['analysis_result'] + "\n"

        # 添加执行计划
        if state['execution_plan']:
            report += "\n## 自动执行计划\n"
            for i, command in enumerate(state['execution_plan'], 1):
                report += f"{i}. `{command}`\n"

        # 添加执行结果
        if state['execution_results']:
            report += "\n## 执行结果\n"
            success_count = len([r for r in state['execution_results'] if r.success])
            report += f"成功执行: {success_count}/{len(state['execution_results'])} 个操作\n"

            # 显示最近的成功和失败操作
            for result in state['execution_results'][-3:]:  # 显示最后3个结果
                status_icon = "✅" if result.success else "❌"
                report += f"- {status_icon} `{result.command}`\n"
                if result.error:
                    report += f"  错误: {result.error}\n"

        # 添加错误信息
        if state.get('error_message'):
            report += f"\n## ⚠️ 错误信息\n{state['error_message']}\n"

        report += f"\n---\n*报告由智能运维助手自动生成*"

        return report

    async def run(self, user_query: str = None) -> Dict[str, Any]:
        """运行智能运维助手"""
        try:
            logger.info("启动智能运维助手...")

            # 重置状态
            self.state_manager.reset_state()

            # 设置用户查询
            if user_query:
                self.state_manager.state["user_query"] = user_query

            # 创建初始状态
            initial_state = self.state_manager.get_state()

            # 运行工作流
            checkpointer = MemorySaver()
            config = {"configurable": {"thread_id": self.state_manager.state["session_id"]}}
            final_state = await self.graph.ainvoke(initial_state, config=config)

            # 更新状态管理器
            self.state_manager.state.update(final_state)

            # 记录对话
            if user_query and final_state.get("ai_response"):
                self.state_manager.add_conversation(user_query, final_state["ai_response"])

            logger.info("智能运维助手运行完成")

            return {
                "success": True,
                "state": final_state,
                "response": final_state.get("ai_response", ""),
                "summary": self.state_manager.get_summary()
            }

        except Exception as e:
            logger.error(f"智能运维助手运行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "state": self.state_manager.get_state(),
                "response": f"智能运维助手运行失败: {str(e)}"
            }

    def get_current_state(self) -> OpsAssistantState:
        """获取当前状态"""
        return self.state_manager.get_state()