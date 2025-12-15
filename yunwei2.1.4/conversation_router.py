#!/usr/bin/env python3
"""
对话路由器 - 智能判断用户意图并路由到相应的处理流程
实现React机制，根据用户需求决定是否执行系统巡检
"""

import re
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from logger_config import get_logger
from langgraph_logger import langgraph_logger

logger = get_logger(__name__)

class IntentType(Enum):
    """用户意图类型"""
    CHAT = "chat"                    # 纯对话，直接LLM回答
    SYSTEM_CHECK = "system_check"    # 系统检查，执行完整巡检
    SYSTEM_INFO = "system_info"      # 系统信息查询
    TROUBLESHOOT = "troubleshoot"    # 故障排查
    COMMAND_EXEC = "command_exec"    # 命令执行
    PERFORMANCE = "performance"      # 性能分析
    OPTIMIZATION = "optimization"    # 系统优化

@dataclass
class IntentAnalysis:
    """意图分析结果"""
    intent_type: IntentType
    confidence: float
    requires_metrics: bool
    requires_execution: bool
    extracted_params: Dict[str, Any]
    reasoning: str

class ConversationRouter:
    """对话路由器 - 分析用户意图并决定处理流程"""

    def __init__(self):
        self.logger = get_logger("conversation_router")

        # 意图识别关键词和模式
        self.intent_patterns = {
            IntentType.SYSTEM_CHECK: [
                r"检查系统", r"系统检查", r"巡检", r"健康检查", r"状态检查",
                r"体检", r"诊断", r"全面检查", r"监控检查", r"全面.*检查"
            ],
            IntentType.CHAT: [
                r"你好", r"谢谢", r"再见", r"帮助", r"介绍", r"什么是",
                r"如何", r"为什么", r"解释", r"聊天", r"对话", r"交流"
            ],
            IntentType.SYSTEM_INFO: [
                r".*cpu.*(?:使用率|情况|状态|是多少|怎么样)", r".*内存.*(?:使用率|情况|状态|是多少|怎么样)",
                r".*磁盘.*(?:使用率|情况|状态|空间)", r".*网络.*(?:状态|情况)",
                r".*负载.*(?:情况|状态)", r".*进程.*(?:情况|状态)",
                r"当前.*状态", r"显示.*信息", r"查看.*(?:cpu|内存|磁盘|网络)",
                r"获取.*(?:cpu|内存|磁盘|网络|指标|数据)",
                r"cpu使用率", r"内存使用率", r"磁盘使用率", r"网络状态",
                r"cpu.*是多少", r"内存.*是多少", r"磁盘.*是多少", r"网络.*怎么样"
            ],
            IntentType.TROUBLESHOOT: [
                r"故障", r"问题", r"错误", r"异常", r"失败", r"不能",
                r"无法", r"解决", r"修复", r"排查", r"诊断.*问题"
            ],
            IntentType.COMMAND_EXEC: [
                r"执行", r"运行", r"启动", r"停止", r"重启", r"删除",
                r"创建", r"修改", r"命令", r"操作"
            ],
            IntentType.PERFORMANCE: [
                r"性能", r"优化", r"慢", r"卡顿", r"延迟", r"速度",
                r"效率", r"瓶颈", r"压力测试", r"负载测试"
            ],
            IntentType.OPTIMIZATION: [
                r"优化", r"清理", r"加速", r"提升", r"改进", r"配置",
                r"调优", r"参数", r"设置"
            ]
        }

        # 强制系统检查的关键词
        self.force_check_keywords = [
            "检查系统", "系统检查", "巡检", "全面检查", "健康检查", "状态检查"
        ]

    def analyze_intent(self, user_query: str, context: Optional[Dict[str, Any]] = None) -> IntentAnalysis:
        """分析用户意图"""
        query_lower = user_query.lower()

        # 记录意图分析开始
        self.logger.info(f"开始分析用户意图: {user_query[:100]}...")

        # 检查是否强制要求系统检查
        for keyword in self.force_check_keywords:
            if keyword in query_lower:
                return IntentAnalysis(
                    intent_type=IntentType.SYSTEM_CHECK,
                    confidence=0.95,
                    requires_metrics=True,
                    requires_execution=False,
                    extracted_params={"force_check": True},
                    reasoning=f"检测到强制检查关键词: {keyword}"
                )

        # 优先检查简单聊天意图（高优先级）
        chat_keywords = ["你好", "hello", "hi", "谢谢", "再见", "帮助", "介绍"]
        for keyword in chat_keywords:
            if keyword in query_lower:
                return IntentAnalysis(
                    intent_type=IntentType.CHAT,
                    confidence=0.98,
                    requires_metrics=False,
                    requires_execution=False,
                    extracted_params={"greeting": keyword},
                    reasoning=f"检测到聊天关键词: {keyword}"
                )

        # 计算各种意图的匹配度
        intent_scores = {}
        for intent_type, patterns in self.intent_patterns.items():
            score = self._calculate_pattern_score(query_lower, patterns)
            intent_scores[intent_type] = score

        # 找到最高分的意图
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[best_intent]

        # 如果最高分数太低，默认为聊天意图
        if confidence < 0.3:
            self.logger.info(f"意图匹配置信度过低 ({confidence:.2f})，默认使用聊天意图")
            best_intent = IntentType.CHAT
            confidence = 0.6

        # 根据意图类型确定是否需要获取指标和执行操作
        requires_metrics = best_intent in [
            IntentType.SYSTEM_CHECK, IntentType.SYSTEM_INFO,
            IntentType.TROUBLESHOOT, IntentType.PERFORMANCE,
            IntentType.OPTIMIZATION
        ]

        requires_execution = best_intent in [
            IntentType.SYSTEM_CHECK, IntentType.COMMAND_EXEC
        ]

        # 提取参数
        extracted_params = self._extract_parameters(user_query, best_intent)

        # 生成推理说明
        reasoning = f"最佳匹配意图: {best_intent.value}, 置信度: {confidence:.2f}"

        result = IntentAnalysis(
            intent_type=best_intent,
            confidence=confidence,
            requires_metrics=requires_metrics,
            requires_execution=requires_execution,
            extracted_params=extracted_params,
            reasoning=reasoning
        )

        # 记录分析结果
        self.logger.info(f"意图分析完成: {result.intent_type.value}, "
                        f"置信度: {result.confidence:.2f}, "
                        f"需要指标: {result.requires_metrics}, "
                        f"需要执行: {result.requires_execution}")

        # 记录到LangGraph日志
        langgraph_logger.log_system_action(
            "意图分析",
            {
                "user_query": user_query,
                "intent_type": result.intent_type.value,
                "confidence": result.confidence,
                "requires_metrics": result.requires_metrics,
                "requires_execution": result.requires_execution,
                "extracted_params": result.extracted_params
            },
            {"analysis_result": result.reasoning},
            success=True
        )

        return result

    def _calculate_pattern_score(self, query: str, patterns: List[str]) -> float:
        """计算模式匹配分数"""
        max_score = 0.0
        for pattern in patterns:
            # 尝试正则匹配
            if re.search(pattern, query):
                # 如果是简单的文本匹配（不是正则），精确匹配得分更高
                if not any(char in pattern for char in r"*.+?[](){}\\") and pattern in query:
                    score = 1.0
                else:
                    score = 0.8
                max_score = max(max_score, score)
            # 如果正则匹配失败，尝试简单的文本包含匹配
            elif pattern in query:
                score = 0.9  # 文本包含匹配得分较高
                max_score = max(max_score, score)
        return max_score

    def _extract_parameters(self, query: str, intent_type: IntentType) -> Dict[str, Any]:
        """从查询中提取参数"""
        params = {}

        if intent_type == IntentType.SYSTEM_INFO:
            # 提取系统资源类型
            resource_types = {
                "cpu": "CPU使用率",
                "memory": "内存使用情况",
                "磁盘": "磁盘使用情况",
                "disk": "磁盘使用情况",
                "网络": "网络状态",
                "network": "网络状态",
                "进程": "进程信息",
                "process": "进程信息",
                "负载": "系统负载",
                "load": "系统负载"
            }

            for key, value in resource_types.items():
                if key in query.lower():
                    params["resource_type"] = key
                    params["resource_name"] = value
                    break

        elif intent_type == IntentType.TROUBLESHOOT:
            # 提取问题描述
            error_patterns = [
                r"(错误|异常|失败)([:：]\s*)(.+)",
                r"(问题|故障)([:：]\s*)(.+)",
                r"(不能|无法|失败)([:：]\s*)(.+)"
            ]

            for pattern in error_patterns:
                match = re.search(pattern, query)
                if match:
                    params["error_description"] = match.group(3).strip()
                    break

        elif intent_type == IntentType.COMMAND_EXEC:
            # 提取命令关键词
            command_keywords = ["启动", "停止", "重启", "删除", "创建", "执行", "运行"]
            for keyword in command_keywords:
                if keyword in query:
                    params["action"] = keyword
                    break

        return params

    def route_to_workflow(self, intent_analysis: IntentAnalysis) -> str:
        """根据意图分析结果路由到相应的工作流"""
        if intent_analysis.intent_type == IntentType.SYSTEM_CHECK:
            return "system_check_workflow"
        elif intent_analysis.intent_type == IntentType.CHAT:
            return "chat_workflow"
        elif intent_analysis.intent_type == IntentType.SYSTEM_INFO:
            return "system_info_workflow"
        elif intent_analysis.intent_type == IntentType.TROUBLESHOOT:
            return "troubleshoot_workflow"
        elif intent_analysis.intent_type == IntentType.COMMAND_EXEC:
            return "command_exec_workflow"
        elif intent_analysis.intent_type in [IntentType.PERFORMANCE, IntentType.OPTIMIZATION]:
            return "performance_analysis_workflow"
        else:
            # 默认使用对话工作流
            return "chat_workflow"

    def should_collect_metrics(self, intent_analysis: IntentAnalysis, context: Optional[Dict[str, Any]] = None) -> bool:
        """判断是否需要收集监控指标"""
        # 如果用户明确要求系统检查，必须收集指标
        if intent_analysis.intent_type == IntentType.SYSTEM_CHECK:
            return True

        # 如果上下文中有最近的指标数据且时间不超过5分钟，可以重用
        if context and "last_metrics_time" in context:
            last_time = context["last_metrics_time"]
            if isinstance(last_time, (int, float)):
                time_diff = time.time() - last_time
                if time_diff < 300:  # 5分钟
                    self.logger.info(f"重用最近的指标数据 (缓存时间: {time_diff:.1f}s)")
                    return False

        # 根据意图决定是否需要最新指标
        return intent_analysis.requires_metrics

    def generate_chat_context(self, intent_analysis: IntentAnalysis,
                            current_metrics: Optional[Dict[str, Any]] = None) -> str:
        """为聊天工作流生成上下文信息"""
        context_parts = []

        # 添加意图信息
        context_parts.append(f"用户意图: {intent_analysis.intent_type.value}")

        if intent_analysis.extracted_params:
            context_parts.append(f"提取参数: {intent_analysis.extracted_params}")

        # 添加系统指标信息（如果有）
        if current_metrics:
            context_parts.append("当前系统指标:")

            # 添加关键指标摘要
            if "cpu_usage" in current_metrics:
                context_parts.append(f"- CPU使用率: {current_metrics['cpu_usage']}%")

            if "memory_usage" in current_metrics:
                context_parts.append(f"- 内存使用率: {current_metrics['memory_usage']}%")

            if "alerts" in current_metrics and current_metrics["alerts"]:
                alert_count = len(current_metrics["alerts"])
                context_parts.append(f"- 活跃告警数: {alert_count}")

        # 添加指导信息
        guidance = self._get_intent_guidance(intent_analysis.intent_type)
        if guidance:
            context_parts.append(f"处理指导: {guidance}")

        return "\n".join(context_parts)

    def _get_intent_guidance(self, intent_type: IntentType) -> str:
        """获取特定意图的处理指导"""
        guidance_map = {
            IntentType.CHAT: "直接与用户对话，提供有用的运维建议和知识",
            IntentType.SYSTEM_INFO: "提供用户查询的系统资源信息，如CPU、内存、磁盘等",
            IntentType.TROUBLESHOOT: "帮助用户分析和解决系统问题",
            IntentType.PERFORMANCE: "分析系统性能状况并提供优化建议",
            IntentType.OPTIMIZATION: "提供系统优化和配置建议"
        }
        return guidance_map.get(intent_type, "")


# 全局对话路由器实例
conversation_router = ConversationRouter()