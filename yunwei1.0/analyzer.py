from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from config import Config
from states import OpsAssistantState, MetricValue, SystemAlert, AlertLevel

logger = logging.getLogger(__name__)

class SystemAnalyzer:
    """系统智能分析器"""

    def __init__(self):
        llm_config = Config.get_llm_config()
        self.llm = ChatOpenAI(**llm_config)
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个专业的Linux系统运维专家和智能运维助手。你的主要职责是：

1. **系统监控分析**：
   - 分析CPU、内存、磁盘、网络等系统指标
   - 识别性能瓶颈和异常情况
   - 评估系统健康状态

2. **问题诊断**：
   - 基于监控数据诊断系统问题
   - 分析问题根本原因
   - 评估问题影响程度

3. **解决方案建议**：
   - 提供具体的修复操作步骤
   - 建议预防性措施
   - 评估操作风险

4. **自动化决策**：
   - 判断是否需要自动修复
   - 确定修复的优先级
   - 生成执行计划

**分析原则**：
- 优先考虑系统稳定性和数据安全
- 遵循最小干预原则
- 提供可操作的具体建议
- 考虑操作的回滚方案

**响应格式**：
- 使用简洁明了的技术语言
- 提供具体的命令和操作步骤
- 包含风险评估和注意事项
- 按优先级排列建议操作

请基于提供的监控数据和系统信息，进行专业的分析和建议。"""

    def analyze_metrics(self, metrics: List[MetricValue], alerts: List[SystemAlert]) -> Dict[str, Any]:
        """分析监控指标和告警"""
        try:
            # 构建分析上下文
            context = self._build_analysis_context(metrics, alerts)

            # 生成分析提示
            analysis_prompt = self._build_analysis_prompt(context)

            # 调用LLM进行分析
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=analysis_prompt)
            ]

            response = self.llm.invoke(messages)
            analysis_text = response.content

            # 解析分析结果
            parsed_result = self._parse_analysis_result(analysis_text)

            return {
                "raw_analysis": analysis_text,
                "detected_issues": parsed_result.get("issues", []),
                "recommended_actions": parsed_result.get("actions", []),
                "risk_assessment": parsed_result.get("risks", []),
                "urgency_level": parsed_result.get("urgency", "medium"),
                "auto_fixable": parsed_result.get("auto_fixable", False)
            }

        except Exception as e:
            logger.error(f"分析监控指标失败: {e}")
            return {
                "raw_analysis": f"分析失败: {str(e)}",
                "detected_issues": ["分析服务异常"],
                "recommended_actions": ["请检查分析器配置"],
                "risk_assessment": ["系统分析不可用"],
                "urgency_level": "high",
                "auto_fixable": False
            }

    def _build_analysis_context(self, metrics: List[MetricValue], alerts: List[SystemAlert]) -> Dict[str, Any]:
        """构建分析上下文"""
        # 按类型分组指标
        cpu_metrics = [m for m in metrics if 'cpu' in m.name.lower()]
        memory_metrics = [m for m in metrics if 'memory' in m.name.lower()]
        disk_metrics = [m for m in metrics if 'disk' in m.name.lower()]
        network_metrics = [m for m in metrics if 'network' in m.name.lower() or 'tcp' in m.name.lower()]
        system_metrics = [m for m in metrics if 'load' in m.name.lower()]

        # 统计告警级别
        critical_alerts = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        warning_alerts = [a for a in alerts if a.level == AlertLevel.WARNING]

        context = {
            "timestamp": datetime.now().isoformat(),
            "metrics_summary": {
                "total_metrics": len(metrics),
                "cpu_metrics": len(cpu_metrics),
                "memory_metrics": len(memory_metrics),
                "disk_metrics": len(disk_metrics),
                "network_metrics": len(network_metrics),
                "system_metrics": len(system_metrics)
            },
            "alerts_summary": {
                "total_alerts": len(alerts),
                "critical_alerts": len(critical_alerts),
                "warning_alerts": len(warning_alerts)
            },
            "detailed_metrics": {
                "cpu": self._format_metrics_for_analysis(cpu_metrics),
                "memory": self._format_metrics_for_analysis(memory_metrics),
                "disk": self._format_metrics_for_analysis(disk_metrics),
                "network": self._format_metrics_for_analysis(network_metrics),
                "system": self._format_metrics_for_analysis(system_metrics)
            },
            "active_alerts": [
                {
                    "metric": alert.metric_name,
                    "level": alert.level.value,
                    "message": alert.message,
                    "value": alert.value,
                    "threshold": alert.threshold,
                    "suggested_actions": alert.suggested_actions
                }
                for alert in alerts
            ]
        }

        return context

    def _format_metrics_for_analysis(self, metrics: List[MetricValue]) -> List[Dict[str, Any]]:
        """格式化指标用于分析"""
        formatted = []
        for metric in metrics:
            formatted.append({
                "name": metric.name,
                "value": metric.value,
                "unit": metric.unit,
                "threshold": metric.threshold,
                "status": metric.status.value,
                "timestamp": metric.timestamp.isoformat()
            })
        return formatted

    def _build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """构建分析提示词"""
        prompt = f"""请分析以下Linux系统监控数据，并提供专业的运维建议：

## 系统监控概览
- 分析时间: {context['timestamp']}
- 总指标数: {context['metrics_summary']['total_metrics']}
- 告警数量: {context['alerts_summary']['total_alerts']} (严重: {context['alerts_summary']['critical_alerts']}, 警告: {context['alerts_summary']['warning_alerts']})

## 关键指标数据

### CPU指标
{self._format_metric_group(context['detailed_metrics']['cpu'])}

### 内存指标
{self._format_metric_group(context['detailed_metrics']['memory'])}

### 磁盘指标
{self._format_metric_group(context['detailed_metrics']['disk'])}

### 网络指标
{self._format_metric_group(context['detailed_metrics']['network'])}

### 系统指标
{self._format_metric_group(context['detailed_metrics']['system'])}

## 活跃告警
{self._format_alerts(context['active_alerts'])}

## 配置的阈值
- CPU使用率阈值: {Config.THRESHOLDS['cpu_usage']}%
- 内存使用率阈值: {Config.THRESHOLDS['memory_usage']}%
- 磁盘使用率阈值: {Config.THRESHOLDS['disk_usage']}%
- 系统负载阈值: {Config.THRESHOLDS['load_average']}

请基于以上数据提供：
1. 系统状态总体评估
2. 检测到的具体问题
3. 详细的解决建议
4. 操作风险评估
5. 是否建议自动修复

请按以下JSON格式回复：
{{
    "overall_status": "healthy|warning|critical",
    "issues": ["问题1", "问题2"],
    "actions": ["具体操作1", "具体操作2"],
    "risks": ["风险1", "风险2"],
    "urgency": "low|medium|high|critical",
    "auto_fixable": true|false
}}
"""

        return prompt

    def _format_metric_group(self, metrics: List[Dict[str, Any]]) -> str:
        """格式化指标组"""
        if not metrics:
            return "无数据"

        lines = []
        for metric in metrics:
            status_indicator = "⚠️" if metric['status'] == 'warning' else "❌" if metric['status'] == 'critical' else "✅"
            threshold_info = f" (阈值: {metric['threshold']})" if metric['threshold'] else ""
            lines.append(f"{status_indicator} {metric['name']}: {metric['value']}{metric['unit']}{threshold_info}")

        return "\n".join(lines)

    def _format_alerts(self, alerts: List[Dict[str, Any]]) -> str:
        """格式化告警信息"""
        if not alerts:
            return "无活跃告警"

        lines = []
        for alert in alerts:
            level_indicator = "🔴" if alert['level'] == 'critical' else "🟡"
            lines.append(f"{level_indicator} {alert['metric']}: {alert['message']}")
            lines.append(f"   当前值: {alert['value']}, 阈值: {alert['threshold']}")
            if alert['suggested_actions']:
                lines.append(f"   建议操作: {', '.join(alert['suggested_actions'])}")
            lines.append("")

        return "\n".join(lines)

    def _parse_analysis_result(self, analysis_text: str) -> Dict[str, Any]:
        """解析LLM分析结果"""
        try:
            import json
            import re

            # 尝试提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', analysis_text)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                return parsed

            # 如果无法解析JSON，返回基本结构
            return {
                "overall_status": "unknown",
                "issues": ["分析结果解析失败"],
                "actions": ["请手动检查系统状态"],
                "risks": ["自动分析不可用"],
                "urgency": "medium",
                "auto_fixable": False
            }

        except Exception as e:
            logger.error(f"解析分析结果失败: {e}")
            return {
                "overall_status": "unknown",
                "issues": ["分析结果解析异常"],
                "actions": ["请查看原始分析结果"],
                "risks": ["自动化分析暂时不可用"],
                "urgency": "medium",
                "auto_fixable": False
            }

    def generate_execution_plan(self, analysis_result: Dict[str, Any]) -> List[str]:
        """基于分析结果生成执行计划"""
        execution_plan = []

        if not analysis_result.get("actions"):
            return execution_plan

        # 根据紧急程度和风险排序操作
        actions = analysis_result["actions"]
        urgency = analysis_result.get("urgency", "medium")
        auto_fixable = analysis_result.get("auto_fixable", False)

        # 只有在建议自动修复时才生成执行计划
        if auto_fixable:
            for action in actions:
                # 将自然语言建议转换为具体命令
                command = self._convert_action_to_command(action)
                if command:
                    execution_plan.append(command)

        return execution_plan

    def _convert_action_to_command(self, action: str) -> Optional[str]:
        """将操作建议转换为具体命令"""
        action_lower = action.lower()

        # CPU相关操作
        if "cpu" in action_lower and ("进程" in action_lower or "process" in action_lower):
            return "ps aux --sort=-%cpu | head -10"

        # 内存相关操作
        if "内存" in action_lower and ("缓存" in action_lower or "cache" in action_lower):
            return "sync && echo 3 > /proc/sys/vm/drop_caches"

        # 磁盘相关操作
        if "磁盘" in action_lower and ("清理" in action_lower or "clean" in action_lower):
            return "find /tmp -type f -atime +7 -delete"

        # 临时文件清理
        if "临时文件" in action_lower or "temp" in action_lower:
            return "find /tmp -type f -size +100M -exec ls -lh {} \\;"

        # 系统状态检查
        if "系统" in action_lower and ("状态" in action_lower or "status" in action_lower):
            return "top -bn1 | head -20"

        # 网络连接检查
        if "网络" in action_lower and ("连接" in action_lower or "connection" in action_lower):
            return "netstat -an | grep ESTABLISHED | wc -l"

        # 如果无法识别，返回系统信息命令
        if "检查" in action_lower or "check" in action_lower:
            return "uptime && free -h && df -h"

        return None

    def get_quick_assessment(self, metrics: List[MetricValue]) -> str:
        """快速系统评估"""
        critical_count = sum(1 for m in metrics if m.status == AlertLevel.CRITICAL)
        warning_count = sum(1 for m in metrics if m.status == AlertLevel.WARNING)

        if critical_count > 0:
            return f"系统状态：严重异常 ({critical_count}个严重告警, {warning_count}个警告)"
        elif warning_count > 0:
            return f"系统状态：警告 ({warning_count}个警告)"
        else:
            return "系统状态：健康"

    def should_trigger_auto_fix(self, analysis_result: Dict[str, Any]) -> bool:
        """判断是否应该触发自动修复"""
        # 基于多个因素判断
        urgency = analysis_result.get("urgency", "low")
        auto_fixable = analysis_result.get("auto_fixable", False)
        critical_issues = len([issue for issue in analysis_result.get("issues", [])
                             if "严重" in issue or "critical" in issue.lower()])

        # 只有在紧急程度高且可自动修复时才触发
        return (urgency in ["high", "critical"] and
                auto_fixable and
                critical_issues > 0)