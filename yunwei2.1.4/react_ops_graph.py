#!/usr/bin/env python3
"""
基于React机制的智能运维助手工作流
支持对话路由和按需执行系统检查
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from states import OpsAssistantState, StateManager, SystemStatus
from monitoring import PrometheusClient
from remote_executor import RemoteExecutor
from analyzer import SystemAnalyzer
from conversation_router import conversation_router, IntentType
from logger_config import get_logger, error_logger, log_operation, log_performance
from langgraph_logger import langgraph_logger, log_langgraph_node, log_langgraph_transition

logger = get_logger(__name__)

class WorkflowType(Enum):
    """工作流类型"""
    CHAT = "chat"
    SYSTEM_CHECK = "system_check"
    SYSTEM_INFO = "system_info"
    TROUBLESHOOT = "troubleshoot"

class ReactOpsAssistantGraph:
    """基于React机制的智能运维助手工作流"""

    def __init__(self):
        self.state_manager = StateManager()
        self.prometheus_client = PrometheusClient()
        self.system_analyzer = SystemAnalyzer()
        self.remote_executor = RemoteExecutor()
        self.logger = get_logger("react_ops_graph")

        # 构建多个工作流
        self.graphs = {
            WorkflowType.CHAT: self._build_chat_graph(),
            WorkflowType.SYSTEM_CHECK: self._build_system_check_graph(),
            WorkflowType.SYSTEM_INFO: self._build_system_info_graph(),
            WorkflowType.TROUBLESHOOT: self._build_troubleshoot_graph()
        }

        # 缓存的指标数据
        self._cached_metrics = None
        self._metrics_cache_time = 0

    def _build_chat_graph(self) -> StateGraph:
        """构建对话工作流"""
        workflow = StateGraph(OpsAssistantState)

        # 添加节点
        workflow.add_node("route_intent", self._route_intent)
        workflow.add_node("chat_response", self._chat_response)
        workflow.add_node("end_conversation", self._end_conversation)

        # 设置入口点
        workflow.set_entry_point("route_intent")

        # 添加边
        workflow.add_edge("route_intent", "chat_response")
        workflow.add_edge("chat_response", "end_conversation")
        workflow.add_edge("end_conversation", END)

        # 创建checkpointer
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    def _build_system_check_graph(self) -> StateGraph:
        """构建系统检查工作流（完整的巡检流程）"""
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

    def _build_system_info_graph(self) -> StateGraph:
        """构建系统信息查询工作流（简化版检查）"""
        workflow = StateGraph(OpsAssistantState)

        # 添加节点
        workflow.add_node("collect_basic_metrics", self._collect_basic_metrics)
        workflow.add_node("provide_system_info", self._provide_system_info)

        # 设置入口点
        workflow.set_entry_point("collect_basic_metrics")

        # 添加边
        workflow.add_edge("collect_basic_metrics", "provide_system_info")
        workflow.add_edge("provide_system_info", END)

        # 创建checkpointer
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    def _build_troubleshoot_graph(self) -> StateGraph:
        """构建故障排查工作流"""
        workflow = StateGraph(OpsAssistantState)

        # 添加节点
        workflow.add_node("collect_relevant_metrics", self._collect_relevant_metrics)
        workflow.add_node("analyze_problem", self._analyze_problem)
        workflow.add_node("provide_solution", self._provide_solution)

        # 设置入口点
        workflow.set_entry_point("collect_relevant_metrics")

        # 添加边
        workflow.add_edge("collect_relevant_metrics", "analyze_problem")
        workflow.add_edge("analyze_problem", "provide_solution")
        workflow.add_edge("provide_solution", END)

        # 创建checkpointer
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    # ==================== 节点实现 ====================

    @log_langgraph_node("route_intent")
    async def _route_intent(self, state: OpsAssistantState) -> OpsAssistantState:
        """路由用户意图"""
        start_time = time.time()

        try:
            user_query = state.get("user_query", "")

            # 分析用户意图
            intent_analysis = conversation_router.analyze_intent(user_query, state.get("context", {}))

            # 存储意图分析结果
            state["intent_analysis"] = intent_analysis
            state["workflow_type"] = intent_analysis.intent_type.value

            # 记录性能
            end_time = time.time()
            log_performance("route_intent", start_time, end_time, {
                "intent_type": intent_analysis.intent_type.value,
                "confidence": intent_analysis.confidence
            })

            self.logger.info(f"意图路由完成: {intent_analysis.intent_type.value}")

            return state

        except Exception as e:
            logger.error(f"意图路由失败: {e}")
            state["error_message"] = f"意图分析失败: {str(e)}"
            return state

    @log_langgraph_node("chat_response")
    async def _chat_response(self, state: OpsAssistantState) -> OpsAssistantState:
        """生成对话响应（不执行系统检查）"""
        start_time = time.time()

        try:
            user_query = state.get("user_query", "")
            intent_analysis = state.get("intent_analysis")

            # 生成聊天上下文
            current_metrics = self._get_cached_metrics() if intent_analysis and intent_analysis.requires_metrics else None
            # 确保传递有效的意图分析对象
            if not intent_analysis:
                # 如果意图分析为空，创建一个默认的聊天意图
                from conversation_router import IntentAnalysis, IntentType
                intent_analysis = IntentAnalysis(
                    intent_type=IntentType.CHAT,
                    confidence=0.5,
                    requires_metrics=False,
                    requires_execution=False,
                    extracted_params={},
                    reasoning="默认聊天意图"
                )
            chat_context = conversation_router.generate_chat_context(intent_analysis, current_metrics)

            # 构建对话提示
            chat_prompt = f"""
你是一个专业的Linux系统运维助手。请基于以下信息回答用户问题：

{chat_context}

用户问题：{user_query}

请提供专业、准确、有用的回答。如果是技术问题，请提供具体的操作建议。
如果用户询问系统状态，请基于当前提供的数据进行分析。
如果需要执行系统检查，请指导用户点击"执行系统检查"按钮。
"""

            # 记录LLM交互开始
            langgraph_logger.log_llm_interaction(
                phase="chat_response",
                prompt=chat_prompt,
                response="",
                model_name="qwen-max"
            )

            # 调用LLM生成回复
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=self.system_analyzer.system_prompt),
                HumanMessage(content=chat_prompt)
            ]

            llm_start_time = time.time()
            response = self.system_analyzer.llm.invoke(messages)
            llm_end_time = time.time()
            ai_response = response.content

            # 记录LLM交互完成
            langgraph_logger.log_llm_interaction(
                phase="chat_response",
                prompt=chat_prompt,
                response=ai_response,
                model_name="qwen-max",
                response_time=llm_end_time - llm_start_time
            )

            # 更新状态
            state["ai_response"] = ai_response
            state["response_type"] = "chat"

            # 记录性能
            end_time = time.time()
            log_performance("chat_response", start_time, end_time, {
                "response_length": len(ai_response),
                "llm_response_time": llm_end_time - llm_start_time
            })

            self.logger.info(f"对话响应生成完成，长度: {len(ai_response)}")

            return state

        except Exception as e:
            logger.error(f"对话响应生成失败: {e}")
            state["error_message"] = f"生成回复失败: {str(e)}"
            return state

    @log_langgraph_node("end_conversation")
    async def _end_conversation(self, state: OpsAssistantState) -> OpsAssistantState:
        """结束对话"""
        try:
            # 记录对话完成
            user_query = state.get("user_query", "")
            ai_response = state.get("ai_response", "")

            langgraph_logger.log_conversation(
                user_query=user_query,
                ai_response=ai_response,
                node_sequence=["route_intent", "chat_response", "end_conversation"],
                success=not state.get("error_message"),
                error_message=state.get("error_message"),
                context_data={
                    "workflow_type": state.get("workflow_type"),
                    "response_type": state.get("response_type"),
                    "intent_analysis": state.get("intent_analysis").__dict__ if state.get("intent_analysis") else None
                }
            )

            return state

        except Exception as e:
            logger.error(f"结束对话失败: {e}")
            return state

    # ==================== 系统检查工作流节点====================

    @log_langgraph_node("collect_metrics")
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

            # 缓存指标数据
            self._cached_metrics = {
                "metrics": metrics,
                "alerts": alerts,
                "timestamp": time.time()
            }
            self._metrics_cache_time = time.time()

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

    @log_langgraph_node("collect_basic_metrics")
    async def _collect_basic_metrics(self, state: OpsAssistantState) -> OpsAssistantState:
        """收集基础指标（用于系统信息查询）"""
        try:
            # 尝试从缓存获取指标
            cached_data = self._get_cached_metrics()
            if cached_data:
                logger.info("使用缓存的指标数据")
                self.state_manager.update_metrics(cached_data["metrics"])
                for alert in cached_data["alerts"]:
                    self.state_manager.add_alert(alert)
                return self.state_manager.get_state()

            # 如果没有缓存，则收集新指标
            return await self._collect_metrics(state)

        except Exception as e:
            logger.error(f"收集基础指标失败: {e}")
            state["error_message"] = f"基础指标收集失败: {str(e)}"
            return state

    @log_langgraph_node("collect_relevant_metrics")
    async def _collect_relevant_metrics(self, state: OpsAssistantState) -> OpsAssistantState:
        """收集相关指标（用于故障排查）"""
        try:
            # 故障排查通常需要最新的指标数据
            return await self._collect_metrics(state)

        except Exception as e:
            logger.error(f"收集相关指标失败: {e}")
            state["error_message"] = f"相关指标收集失败: {str(e)}"
            return state

    @log_langgraph_node("provide_system_info")
    async def _provide_system_info(self, state: OpsAssistantState) -> OpsAssistantState:
        """提供系统信息响应"""
        try:
            user_query = state.get("user_query", "")
            intent_analysis = state.get("intent_analysis")
            metrics = state.get("metrics", [])
            alerts = state.get("alerts", [])

            # 生成系统信息报告
            info_response = self._generate_system_info_report(user_query, intent_analysis, metrics, alerts)

            state["ai_response"] = info_response
            state["response_type"] = "system_info"

            return state

        except Exception as e:
            logger.error(f"生成系统信息失败: {e}")
            state["error_message"] = f"系统信息生成失败: {str(e)}"
            return state

    @log_langgraph_node("analyze_problem")
    async def _analyze_problem(self, state: OpsAssistantState) -> OpsAssistantState:
        """分析问题"""
        try:
            user_query = state.get("user_query", "")
            intent_analysis = state.get("intent_analysis")
            metrics = state.get("metrics", [])
            alerts = state.get("alerts", [])

            # 使用LLM分析问题
            problem_analysis = self._analyze_problem_with_llm(user_query, intent_analysis, metrics, alerts)

            state["problem_analysis"] = problem_analysis
            return state

        except Exception as e:
            logger.error(f"问题分析失败: {e}")
            state["error_message"] = f"问题分析失败: {str(e)}"
            return state

    @log_langgraph_node("provide_solution")
    async def _provide_solution(self, state: OpsAssistantState) -> OpsAssistantState:
        """提供解决方案"""
        try:
            user_query = state.get("user_query", "")
            problem_analysis = state.get("problem_analysis", "")

            # 生成解决方案
            solution_response = self._generate_solution_response(user_query, problem_analysis)

            state["ai_response"] = solution_response
            state["response_type"] = "solution"

            return state

        except Exception as e:
            logger.error(f"解决方案生成失败: {e}")
            state["error_message"] = f"解决方案生成失败: {str(e)}"
            return state

    # ==================== 辅助方法 ====================

    def _get_cached_metrics(self) -> Optional[Dict[str, Any]]:
        """获取缓存的指标数据"""
        if self._cached_metrics and self._metrics_cache_time:
            age = time.time() - self._metrics_cache_time
            if age < 300:  # 5分钟缓存
                return self._cached_metrics
        return None

    def _generate_system_info_report(self, user_query: str, intent_analysis, metrics: List, alerts: List) -> str:
        """生成系统信息报告"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        report = f"# 系统信息报告\n\n**生成时间**: {timestamp}\n\n"

        # 根据用户查询的参数提供特定信息
        if intent_analysis and intent_analysis.extracted_params:
            resource_type = intent_analysis.extracted_params.get("resource_type")
            if resource_type:
                report += f"## {intent_analysis.extracted_params.get('resource_name', resource_type.upper())} 信息\n\n"
                # 添加特定资源的信息
                # ... 这里可以根据resource_type提供详细信息

        # 添加总体系统状态
        report += "## 系统状态概览\n\n"
        report += f"- 监控指标数量: {len(metrics)}\n"
        report += f"- 活跃告警数量: {len(alerts)}\n"

        if metrics:
            report += "\n### 关键指标\n"
            # 显示前几个关键指标
            for metric in metrics[:5]:
                status_icon = "✅" if metric.status.value == 'normal' else "⚠️" if metric.status.value == 'warning' else "❌"
                report += f"- {status_icon} **{metric.name}**: {metric.value}{metric.unit}\n"

        if alerts:
            report += "\n### 当前告警\n"
            for alert in alerts[:3]:
                level_icon = "🔴" if alert.level.value == 'critical' else "🟡"
                report += f"- {level_icon} **{alert.metric_name}**: {alert.message}\n"

        report += f"\n---\n*报告由智能运维助手自动生成*"

        return report

    def _analyze_problem_with_llm(self, user_query: str, intent_analysis, metrics: List, alerts: List) -> str:
        """使用LLM分析问题"""
        # 构建分析提示
        analysis_prompt = f"""
请分析以下系统问题：

用户描述: {user_query}
提取的参数: {intent_analysis.extracted_params if intent_analysis else {}}

当前系统状态:
- 监控指标数量: {len(metrics)}
- 活跃告警数量: {len(alerts)}

请分析可能的问题原因并提供初步的诊断结果。
"""

        # 调用LLM进行分析
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content="你是一个专业的系统故障诊断专家。"),
            HumanMessage(content=analysis_prompt)
        ]

        response = self.system_analyzer.llm.invoke(messages)
        return response.content

    def _generate_solution_response(self, user_query: str, problem_analysis: str) -> str:
        """生成解决方案响应"""
        solution_prompt = f"""
基于以下问题分析，请提供详细的解决方案：

用户问题: {user_query}
问题分析: {problem_analysis}

请提供：
1. 问题的根本原因
2. 具体的解决步骤
3. 预防措施
4. 如果需要，相关的命令示例
"""

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content="你是一个专业的系统问题解决专家。"),
            HumanMessage(content=solution_prompt)
        ]

        response = self.system_analyzer.llm.invoke(messages)
        return response.content

    # ==================== 状态转换检查函数 ====================

    @log_langgraph_transition("collect_metrics", "metrics_success_check")
    def _check_metrics_success(self, state: OpsAssistantState) -> str:
        """检查指标收集是否成功"""
        if state.get("error_message"):
            return "error"
        if not state["metrics"]:
            return "error"
        return "success"

    @log_langgraph_transition("analyze_system", "analysis_result_check")
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

    @log_langgraph_transition("generate_plan", "plan_executable_check")
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

    # ==================== 复用原有节点 ====================

    @log_langgraph_node("analyze_system")
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

            # 如果有修复计划，保存到状态中（但保留用户已经编辑过的方案）
            if "fix_plans" in parsed_result:
                existing_plans = self.state_manager.state.get("fix_plans", [])

                # 如果用户已经编辑过方案（有修改标记），则保留用户编辑的版本
                if existing_plans and any(plan.get("_user_edited", False) for plan in existing_plans):
                    logger.info("检测到用户编辑过的方案，保留用户版本")
                    # 不覆盖用户编辑过的方案
                else:
                    # 使用新分析生成的方案
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

    @log_langgraph_node("generate_plan")
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

    @log_langgraph_node("execute_plan")
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

    @log_langgraph_node("report_results")
    async def _report_results(self, state: OpsAssistantState) -> OpsAssistantState:
        """报告结果"""
        try:
            logger.info("生成运维报告...")

            # 生成综合报告
            report = self._generate_report(state)

            # 更新AI响应
            state["ai_response"] = report
            state["response_type"] = "system_check"

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

    @log_langgraph_node("handle_errors")
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
        state["response_type"] = "error"

        # 记录错误操作
        self.state_manager.add_action("handle_errors", {
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        })

        return state

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

    # ==================== 主要运行接口 ====================

    async def run(self, user_query: str = None) -> Dict[str, Any]:
        """运行React智能运维助手"""
        start_time = time.time()
        session_id = self.state_manager.state.get("session_id", f"react_session_{int(time.time())}")

        try:
            logger.info("启动React智能运维助手...")

            # 开始会话日志
            langgraph_logger.start_session(session_id, user_query or "")

            # 记录系统操作
            langgraph_logger.log_system_action(
                "启动React运维助手",
                {"user_query": user_query, "session_id": session_id}
            )

            # 重置状态
            self.state_manager.reset_state()

            # 设置用户查询
            if user_query:
                self.state_manager.state["user_query"] = user_query

            # 创建初始状态
            initial_state = self.state_manager.get_state()

            # 首先分析意图
            intent_analysis = conversation_router.analyze_intent(user_query or "")

            # 根据意图选择工作流
            if intent_analysis.intent_type == IntentType.SYSTEM_CHECK:
                workflow = self.graphs[WorkflowType.SYSTEM_CHECK]
            elif intent_analysis.intent_type == IntentType.SYSTEM_INFO:
                workflow = self.graphs[WorkflowType.SYSTEM_INFO]
            elif intent_analysis.intent_type == IntentType.TROUBLESHOOT:
                workflow = self.graphs[WorkflowType.TROUBLESHOOT]
            else:
                # 默认使用对话工作流
                workflow = self.graphs[WorkflowType.CHAT]

            self.logger.info(f"选择工作流: {workflow}")

            # 运行选定的工作流
            config = {"configurable": {"thread_id": session_id}}
            final_state = await workflow.ainvoke(initial_state, config=config)

            # 更新状态管理器
            self.state_manager.state.update(final_state)

            # 获取节点执行序列（从日志中收集）
            node_sequence = langgraph_logger.node_stack.copy()

            # 记录对话
            if user_query and final_state.get("ai_response"):
                self.state_manager.add_conversation(user_query, final_state["ai_response"])

                # 记录到LangGraph对话日志
                langgraph_logger.log_conversation(
                    user_query=user_query,
                    ai_response=final_state["ai_response"],
                    node_sequence=node_sequence,
                    success=not final_state.get("error_message"),
                    error_message=final_state.get("error_message"),
                    context_data={
                        "session_id": session_id,
                        "workflow_type": intent_analysis.intent_type.value,
                        "response_type": final_state.get("response_type"),
                        "system_status": final_state.get("system_status"),
                        "metrics_count": len(final_state.get("metrics", [])),
                        "alerts_count": len(final_state.get("alerts", []))
                    }
                )

            end_time = time.time()
            processing_time = end_time - start_time

            logger.info(f"React智能运维助手运行完成 (耗时: {processing_time:.2f}s)")

            # 结束会话日志
            langgraph_logger.end_session()

            return {
                "success": True,
                "state": final_state,
                "response": final_state.get("ai_response", ""),
                "summary": self.state_manager.get_summary(),
                "session_id": session_id,
                "processing_time": processing_time,
                "workflow_type": intent_analysis.intent_type.value,
                "response_type": final_state.get("response_type", "unknown")
            }

        except Exception as e:
            logger.error(f"React智能运维助手运行失败: {e}")

            # 记录失败对话
            if user_query:
                langgraph_logger.log_conversation(
                    user_query=user_query,
                    ai_response=f"系统错误: {str(e)}",
                    node_sequence=langgraph_logger.node_stack.copy(),
                    success=False,
                    error_message=str(e)
                )

            # 结束会话日志
            langgraph_logger.end_session()

            return {
                "success": False,
                "error": str(e),
                "state": self.state_manager.get_state(),
                "response": f"React智能运维助手运行失败: {str(e)}",
                "session_id": session_id
            }

    def get_current_state(self) -> OpsAssistantState:
        """获取当前状态"""
        return self.state_manager.get_state()