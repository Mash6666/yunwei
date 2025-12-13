from typing import Dict, List, Optional, Any, TypedDict
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class AlertLevel(Enum):
    """告警级别枚举"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"

class SystemStatus(Enum):
    """系统状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class MetricValue:
    """监控指标值"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    threshold: Optional[float] = None
    status: AlertLevel = AlertLevel.NORMAL

@dataclass
class SystemAlert:
    """系统告警"""
    metric_name: str
    level: AlertLevel
    message: str
    value: float
    threshold: float
    timestamp: datetime
    suggested_actions: List[str]

@dataclass
class ExecutionResult:
    """命令执行结果"""
    command: str
    success: bool
    output: str
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class OpsAssistantState(TypedDict):
    """智能运维助手状态管理"""
    # 基础状态
    session_id: str
    timestamp: datetime
    system_status: SystemStatus

    # 监控数据
    metrics: List[MetricValue]
    alerts: List[SystemAlert]

    # 分析结果
    analysis_result: Optional[str]
    detected_issues: List[str]

    # 执行状态
    execution_plan: List[str]
    execution_results: List[ExecutionResult]

    # 用户交互
    user_query: Optional[str]
    ai_response: Optional[str]
    requires_approval: bool

    # 配置和上下文
    context: Dict[str, Any]
    error_message: Optional[str]

    # 历史记录
    conversation_history: List[Dict[str, str]]
    action_history: List[Dict[str, Any]]

class StateManager:
    """状态管理器"""

    def __init__(self):
        self.state: OpsAssistantState = {
            "session_id": self._generate_session_id(),
            "timestamp": datetime.now(),
            "system_status": SystemStatus.UNKNOWN,
            "metrics": [],
            "alerts": [],
            "analysis_result": None,
            "detected_issues": [],
            "execution_plan": [],
            "execution_results": [],
            "user_query": None,
            "ai_response": None,
            "requires_approval": False,
            "context": {},
            "error_message": None,
            "conversation_history": [],
            "action_history": []
        }

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        import uuid
        return str(uuid.uuid4())

    def update_metrics(self, metrics: List[MetricValue]):
        """更新监控指标"""
        self.state["metrics"] = metrics
        self.state["timestamp"] = datetime.now()

    def add_alert(self, alert: SystemAlert):
        """添加告警"""
        self.state["alerts"].append(alert)

        # 更新系统状态
        if alert.level == AlertLevel.CRITICAL:
            self.state["system_status"] = SystemStatus.CRITICAL
        elif alert.level == AlertLevel.WARNING and self.state["system_status"] == SystemStatus.HEALTHY:
            self.state["system_status"] = SystemStatus.WARNING

    def update_analysis(self, result: str, issues: List[str]):
        """更新分析结果"""
        self.state["analysis_result"] = result
        self.state["detected_issues"] = issues

    def set_execution_plan(self, plan: List[str]):
        """设置执行计划"""
        self.state["execution_plan"] = plan
        self.state["requires_approval"] = len(plan) > 0

    def add_execution_result(self, result: ExecutionResult):
        """添加执行结果"""
        self.state["execution_results"].append(result)

    def add_conversation(self, user_msg: str, ai_msg: str):
        """添加对话记录"""
        self.state["conversation_history"].append({
            "user": user_msg,
            "ai": ai_msg,
            "timestamp": datetime.now().isoformat()
        })

    def add_action(self, action_type: str, details: Dict[str, Any]):
        """添加操作记录"""
        self.state["action_history"].append({
            "type": action_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def reset_state(self):
        """重置状态"""
        self.state.update({
            "metrics": [],
            "alerts": [],
            "analysis_result": None,
            "detected_issues": [],
            "execution_plan": [],
            "execution_results": [],
            "error_message": None,
            "system_status": SystemStatus.UNKNOWN
        })

    def get_state(self) -> OpsAssistantState:
        """获取当前状态"""
        return self.state.copy()

    def get_summary(self) -> str:
        """获取状态摘要"""
        metrics_count = len(self.state["metrics"])
        alerts_count = len(self.state["alerts"])
        critical_alerts = len([a for a in self.state["alerts"] if a.level == AlertLevel.CRITICAL])

        summary = f"系统状态: {self.state['system_status'].value}\n"
        summary += f"监控指标: {metrics_count}个\n"
        summary += f"告警数量: {alerts_count}个 (严重: {critical_alerts})\n"

        if self.state["detected_issues"]:
            summary += f"检测到问题: {len(self.state['detected_issues'])}个\n"

        if self.state["execution_plan"]:
            summary += f"待执行操作: {len(self.state['execution_plan'])}个\n"

        return summary