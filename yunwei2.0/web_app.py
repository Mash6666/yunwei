#!/usr/bin/env python3
"""
智能运维助手Web应用
基于FastAPI的后端服务
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 导入智能运维助手组件
from ops_graph import OpsAssistantGraph
from monitoring import PrometheusClient
from remote_executor import RemoteExecutor
from config import Config
from analyzer import SystemAnalyzer

# 配置日志
logger = logging.getLogger(__name__)

app = FastAPI(title="智能运维助手API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

# 全局变量
ops_assistant = OpsAssistantGraph()
active_connections: List[WebSocket] = []

# 辅助函数：处理datetime对象的JSON序列化
def serialize_datetime(obj):
    """递归地将datetime对象转换为字符串"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_datetime(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        # 处理自定义对象
        return {key: serialize_datetime(value) for key, value in obj.__dict__.items() if not key.startswith('_')}
    else:
        return obj

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # 连接已断开，从列表中移除
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Pydantic模型
class SystemStatusResponse(BaseModel):
    status: str
    metrics_count: int
    alerts_count: int
    timestamp: str
    data: Dict[str, Any]

class MetricsResponse(BaseModel):
    cpu_metrics: List[Dict[str, Any]]
    memory_metrics: List[Dict[str, Any]]
    disk_metrics: List[Dict[str, Any]]
    network_metrics: List[Dict[str, Any]]
    system_metrics: List[Dict[str, Any]]
    timestamp: str

class AlertResponse(BaseModel):
    alerts: List[Dict[str, Any]]
    count: int
    critical_count: int
    warning_count: int

class CheckRequest(BaseModel):
    auto_fix: bool = False

class ExecuteCommandRequest(BaseModel):
    command: str

class ChatRequest(BaseModel):
    message: str

class FixPlanRequest(BaseModel):
    plan_id: str

class ExecutionAnalysisRequest(BaseModel):
    execution_results: Dict[str, Any]

class SaveFixPlansRequest(BaseModel):
    fix_plans: List[Dict[str, Any]]

class CommandEditRequest(BaseModel):
    plan_id: str
    command_index: int
    new_command: str
    original_command: Optional[str] = None

# API路由
@app.get("/", response_class=HTMLResponse)
async def root():
    """主页"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/status", response_model=SystemStatusResponse)
async def get_system_status():
    """获取系统状态"""
    try:
        state = ops_assistant.get_current_state()

        # 统计信息
        alerts = state.get('alerts', [])
        critical_count = len([a for a in alerts if hasattr(a, 'level') and hasattr(a.level, 'value') and a.level.value == 'critical'])
        warning_count = len([a for a in alerts if hasattr(a, 'level') and hasattr(a.level, 'value') and a.level.value == 'warning'])

        # 处理系统状态
        system_status = state.get('system_status')
        if hasattr(system_status, 'value'):
            status_value = system_status.value
        else:
            status_value = str(system_status) if system_status else 'unknown'

        # 处理最后检查时间
        last_check = state.get('timestamp')
        if isinstance(last_check, datetime):
            last_check = last_check.isoformat()
        else:
            last_check = str(last_check) if last_check else ''

        return SystemStatusResponse(
            status=status_value,
            metrics_count=len(state.get('metrics', [])),
            alerts_count=len(alerts),
            timestamp=datetime.now().isoformat(),
            data={
                "critical_alerts": critical_count,
                "warning_alerts": warning_count,
                "execution_plan_count": len(state.get('execution_plan', [])),
                "last_check": last_check,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics():
    """获取监控指标"""
    try:
        # 获取最新的监控数据
        prometheus = PrometheusClient()
        metrics = prometheus.fetch_metrics()

        # 按类型分组并序列化
        cpu_metrics = [serialize_datetime(m.__dict__) for m in metrics if 'cpu' in m.name.lower()]
        memory_metrics = [serialize_datetime(m.__dict__) for m in metrics if 'memory' in m.name.lower()]
        disk_metrics = [serialize_datetime(m.__dict__) for m in metrics if 'disk' in m.name.lower()]
        network_metrics = [serialize_datetime(m.__dict__) for m in metrics if 'network' in m.name.lower() or 'tcp' in m.name.lower()]
        system_metrics = [serialize_datetime(m.__dict__) for m in metrics if 'load' in m.name.lower()]

        return MetricsResponse(
            cpu_metrics=cpu_metrics,
            memory_metrics=memory_metrics,
            disk_metrics=disk_metrics,
            network_metrics=network_metrics,
            system_metrics=system_metrics,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts", response_model=AlertResponse)
async def get_alerts():
    """获取告警信息"""
    try:
        prometheus = PrometheusClient()
        metrics = prometheus.fetch_metrics()
        alerts = prometheus.detect_alerts(metrics)

        critical_count = len([a for a in alerts if a.level.value == 'critical'])
        warning_count = len([a for a in alerts if a.level.value == 'warning'])

        return AlertResponse(
            alerts=[serialize_datetime(alert.__dict__) for alert in alerts],
            count=len(alerts),
            critical_count=critical_count,
            warning_count=warning_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/check")
async def run_system_check(request: CheckRequest):
    """执行系统检查"""
    try:
        # 通过WebSocket广播开始检查的消息
        await manager.broadcast(json.dumps({
            "type": "check_started",
            "message": "开始执行系统检查...",
            "timestamp": datetime.now().isoformat()
        }))

        # 执行检查
        result = await ops_assistant.run("执行系统检查")

        if result["success"]:
            # 序列化处理datetime对象
            safe_result = serialize_datetime(result)

            # 获取修复方案
            state = result.get("state", {})
            fix_plans = state.get("fix_plans", [])

            await manager.broadcast(json.dumps({
                "type": "check_completed",
                "message": "系统检查完成",
                "data": safe_result,
                "fix_plans": serialize_datetime(fix_plans),
                "state": serialize_datetime(state),
                "timestamp": datetime.now().isoformat()
            }))

            # 获取状态数据
            state = result.get("state", {})
            system_status = state.get("system_status", {})
            status_value = system_status.value if hasattr(system_status, "value") else str(system_status)

            return {
                "success": True,
                "message": "系统检查完成",
                "data": {
                    "status": status_value,
                    "metrics_count": len(state.get("metrics", [])),
                    "alerts_count": len(state.get("alerts", [])),
                    "summary": result.get("summary", ""),
                    "response": result.get("response", ""),
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            error_message = result.get('error', '未知错误')
            await manager.broadcast(json.dumps({
                "type": "check_failed",
                "message": f"系统检查失败: {error_message}",
                "timestamp": datetime.now().isoformat()
            }))

            return {
                "success": False,
                "message": "系统检查失败",
                "error": error_message
            }

    except Exception as e:
        error_msg = f"检查过程中发生错误: {str(e)}"
        await manager.broadcast(json.dumps({
            "type": "check_error",
            "message": error_msg,
            "timestamp": datetime.now().isoformat()
        }))

        return {
            "success": False,
            "message": "检查失败",
            "error": error_msg
        }

@app.post("/api/execute")
async def execute_command(request: ExecuteCommandRequest):
    """执行远程命令"""
    try:
        with RemoteExecutor() as executor:
            result = executor.execute_command(request.command)
            return {
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "execution_time": result.execution_time
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    """与AI助手对话"""
    try:
        message = request.message.strip()
        if not message:
            return {
                "success": False,
                "response": "请输入你的问题"
            }

        # 获取当前系统状态用于上下文
        state = ops_assistant.get_current_state()
        system_status = state.get('system_status', 'unknown')
        metrics_count = len(state.get('metrics', []))
        alerts_count = len(state.get('alerts', []))

        # 构建上下文信息
        context = f"""
当前系统状态: {system_status}
监控指标数量: {metrics_count}
活跃告警数量: {alerts_count}

用户问题: {message}

请基于当前系统状态回答用户的问题，提供专业的运维建议。
如果用户询问系统检查，请指导用户点击"执行系统检查"按钮，不要自动执行检查。
如果用户询问具体指标，请提供当前数据和分析。
"""

        # 使用系统分析器处理对话
        analyzer = SystemAnalyzer()

        try:
            # 构建对话提示
            chat_prompt = f"""
你是一个专业的Linux系统运维助手。请基于以下信息回答用户问题：

{context}

请提供专业、准确、有用的回答。如果是技术问题，请提供具体的操作建议。
"""

            # 调用LLM生成回复
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=analyzer.system_prompt),
                HumanMessage(content=chat_prompt)
            ]

            response = analyzer.llm.invoke(messages)
            ai_response = response.content

            # 保存对话历史
            ops_assistant.state_manager.add_conversation(message, ai_response)

            return {
                "success": True,
                "response": ai_response,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as llm_error:
            # 如果LLM调用失败，提供预设的智能回复
            predefined_responses = {
                'status': f'当前系统状态为: {system_status}。系统中监测到{metrics_count}个性能指标和{alerts_count}个活跃告警。',
                'check': '如需执行系统检查，请点击控制台页面中的"执行系统检查"按钮。这会触发AI分析系统状态并生成修复方案。',
                'cpu': f'当前监控到{metrics_count}个系统指标。请查看监控指标页面获取详细的CPU使用率数据，包括实时使用情况、系统负载等信息。',
                'memory': '内存使用情况请查看监控指标页面。如果内存使用率过高，建议检查内存占用高的进程，考虑清理系统缓存或重启相关服务。',
                'disk': '磁盘使用情况请查看监控指标页面。建议定期清理临时文件、日志文件和不需要的数据，确保有足够的磁盘空间。',
                'alerts': f'当前系统有{alerts_count}个活跃告警。请查看告警管理页面了解详细信息，并根据AI建议采取相应措施。',
                'optimize': '系统优化建议：1) 监控CPU和内存使用率，避免资源瓶颈 2) 定期清理临时文件和日志 3) 及时更新系统补丁 4) 优化数据库查询 5) 监控网络连接数',
                'default': '我建议您查看系统控制台了解当前状态，或者询问具体的技术问题，如CPU使用率、内存情况、磁盘空间等。我会根据实时数据提供专业的建议。'
            }

            # 根据用户问题类型匹配预设回复
            response_text = predefined_responses.get('default', predefined_responses['status'])

            # 检查消息关键词
            message_lower = message.lower()
            for key, response in predefined_responses.items():
                if key != 'default' and key in message_lower:
                    response_text = response
                    break

            return {
                "success": True,
                "response": response_text,
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"AI对话处理失败: {e}")
        return {
            "success": False,
            "response": "抱歉，我现在无法处理你的请求。请稍后再试，或者尝试询问更具体的问题。"
        }

@app.get("/api/config")
async def get_config():
    """获取配置信息"""
    try:
        return {
            "server_host": Config.SERVER_HOST,
            "prometheus_url": Config.PROMETHEUS_URL,
            "llm_model": Config.LLM_MODEL,
            "thresholds": Config.THRESHOLDS
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_history():
    """获取操作历史"""
    try:
        state = ops_assistant.get_current_state()
        return {
            "action_history": serialize_datetime(state.get('action_history', [])),
            "conversation_history": serialize_datetime(state.get('conversation_history', []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/fix-plans")
async def get_fix_plans():
    """获取修复方案"""
    try:
        state = ops_assistant.get_current_state()
        fix_plans = state.get('fix_plans', [])

        return {
            "success": True,
            "fix_plans": serialize_datetime(fix_plans),
            "count": len(fix_plans),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/fix-plans/approve")
async def approve_fix_plan(request: FixPlanRequest):
    """批准并执行修复方案"""
    global last_execution_results
    try:
        plan_id = request.plan_id
        logger.info(f"用户批准修复方案: {plan_id}")

        # 获取当前状态和修复方案
        state = ops_assistant.get_current_state()
        fix_plans = state.get('fix_plans', [])

        # 查找指定的修复方案
        selected_plan = None

        # 首先从状态管理器中查找
        for plan in fix_plans:
            if plan.get('id') == plan_id:
                selected_plan = plan
                break

        # 如果没找到，尝试索引方式
        if not selected_plan:
            try:
                plan_index = int(plan_id.replace('plan_', '')) - 1
                if 0 <= plan_index < len(fix_plans):
                    selected_plan = fix_plans[plan_index]
            except (ValueError, IndexError):
                pass

        # 如果是followup_plan类型，从多个来源中获取
        if not selected_plan and ('followup_plan' in plan_id or 'followup' in plan_id):
            # 尝试从状态管理器中获取最新方案
            current_fix_plans = ops_assistant.state_manager.state.get('fix_plans', [])
            for plan in current_fix_plans:
                if plan.get('id') == plan_id:
                    selected_plan = plan
                    break

            # 如果没找到，尝试从全局last_execution_results中获取
            if not selected_plan:
                if last_execution_results:
                    # 检查new_fix_plans
                    if 'new_fix_plans' in last_execution_results:
                        new_fix_plans = last_execution_results['new_fix_plans']
                        for plan in new_fix_plans:
                            if plan.get('id') == plan_id:
                                selected_plan = plan
                                break

                    # 检查analysis结果
                    if not selected_plan and 'analysis' in last_execution_results:
                        analysis = last_execution_results['analysis']
                        if analysis.get('fix_plans'):
                            analysis_fix_plans = analysis['fix_plans']
                            for plan in analysis_fix_plans:
                                if plan.get('id') == plan_id:
                                    selected_plan = plan
                                    break

            # 如果还是没找到，尝试模糊匹配followup相关方案
            if not selected_plan:
                for plan in current_fix_plans:
                    if ((plan.get('id') and ('followup' in str(plan.get('id')).lower() or 'followup_plan' in str(plan.get('id')).lower())) or
                       (plan.get('issue') and 'followup' in str(plan.get('issue')).lower())):
                        selected_plan = plan
                        break

        # 如果还是没找到，尝试模糊匹配
        if not selected_plan:
            for plan in fix_plans:
                if (plan.get('id') and plan_id in str(plan.get('id'))) or \
                   (plan.get('issue') and plan_id in str(plan.get('issue'))):
                    selected_plan = plan
                    break

        logger.info(f"找到修复方案: {selected_plan is not None}")

        if not selected_plan:
            return {
                "success": False,
                "error": f"未找到修复方案: {plan_id}，请重新执行系统检查"
            }

        # 通过WebSocket广播执行开始的消息
        await manager.broadcast(json.dumps({
            "type": "execution_started",
            "message": "开始执行修复方案...",
            "plan_id": plan_id,
            "timestamp": datetime.now().isoformat()
        }))

        # 执行修复方案
        execution_results = []
        total_success = True
        start_time = datetime.now()

        # 获取修复计划中的命令
        commands = selected_plan.get('commands', [])

        if commands:
            with RemoteExecutor() as executor:
                for i, cmd in enumerate(commands):
                    command_str = cmd.get('command', '')
                    timeout = cmd.get('timeout', 30)

                    if not command_str:
                        continue

                    logger.info(f"执行命令 {i+1}/{len(commands)}: {command_str}")

                    try:
                        # 执行命令
                        result = executor.execute_command(command_str, timeout=timeout)

                        execution_result = {
                            "step": i + 1,
                            "command": command_str,
                            "success": result.success,
                            "output": result.output,
                            "error": result.error,
                            "execution_time": result.execution_time,
                            "timestamp": datetime.now().isoformat()
                        }

                        execution_results.append(execution_result)

                        if not result.success:
                            total_success = False
                            logger.warning(f"命令执行失败: {command_str}, 错误: {result.error}")

                    except Exception as e:
                        logger.error(f"命令执行异常: {command_str}, 异常: {e}")
                        execution_result = {
                            "step": i + 1,
                            "command": command_str,
                            "success": False,
                            "output": "",
                            "error": str(e),
                            "execution_time": 0,
                            "timestamp": datetime.now().isoformat()
                        }
                        execution_results.append(execution_result)
                        total_success = False

        # 计算总执行时间
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        # 更新状态管理器
        for exec_result in execution_results:
            from states import ExecutionResult
            result_obj = ExecutionResult(
                command=exec_result['command'],
                success=exec_result['success'],
                output=exec_result['output'],
                error=exec_result.get('error'),
                execution_time=exec_result['execution_time'],
                timestamp=datetime.fromisoformat(exec_result['timestamp'])
            )
            ops_assistant.state_manager.add_execution_result(result_obj)

        # 构建执行结果
        result_data = {
            "plan_id": plan_id,
            "completed": True,
            "success": total_success,
            "total_time": total_time,
            "commands": execution_results,
            "timestamp": datetime.now().isoformat()
        }

        # 保存执行结果到全局变量，供前端查询
        last_execution_results = result_data

        # 通过WebSocket广播执行完成的消息
        await manager.broadcast(json.dumps({
            "type": "execution_completed",
            "message": "修复方案执行完成",
            "plan_id": plan_id,
            "success": total_success,
            "timestamp": datetime.now().isoformat()
        }))

        return {
            "success": True,
            "message": "修复方案执行完成",
            "results": result_data
        }

    except Exception as e:
        logger.error(f"执行修复方案失败: {e}")
        await manager.broadcast(json.dumps({
            "type": "execution_failed",
            "message": f"修复方案执行失败: {str(e)}",
            "plan_id": plan_id,
            "timestamp": datetime.now().isoformat()
        }))

        return {
            "success": False,
            "error": f"执行修复方案失败: {str(e)}"
        }

@app.post("/api/fix-plans/reject")
async def reject_fix_plan(request: FixPlanRequest):
    """拒绝修复方案"""
    try:
        plan_id = request.plan_id
        logger.info(f"用户拒绝修复方案: {plan_id}")

        # 记录拒绝操作
        ops_assistant.state_manager.add_action("reject_fix_plan", {
            "plan_id": plan_id,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "success": True,
            "message": f"修复方案 {plan_id} 已被拒绝",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"拒绝修复方案失败: {e}")
        return {
            "success": False,
            "error": f"拒绝修复方案失败: {str(e)}"
        }

@app.get("/api/execution-results")
async def get_execution_results(plan_id: str = None):
    """获取执行结果"""
    try:
        global last_execution_results

        if plan_id and hasattr(ops_assistant.state_manager, 'execution_results'):
            # 从状态管理器获取结果
            execution_results = ops_assistant.state_manager.state.get('execution_results', [])

            # 按plan_id过滤（如果提供）
            if plan_id:
                # 简单处理：返回最近的执行结果
                recent_results = execution_results[-10:]  # 最近10个结果

                return {
                    "success": True,
                    "results": {
                        "plan_id": plan_id,
                        "completed": True,
                        "commands": serialize_datetime(recent_results),
                        "total_time": sum(r.execution_time for r in recent_results),
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                return {
                    "success": True,
                    "results": {
                        "commands": serialize_datetime(execution_results),
                        "timestamp": datetime.now().isoformat()
                    }
                }

        # 如果有全局的执行结果，返回它
        if 'last_execution_results' in globals():
            return {
                "success": True,
                "results": globals()['last_execution_results']
            }

        # 没有执行结果
        return {
            "success": True,
            "results": {
                "completed": False,
                "commands": [],
                "message": "暂无执行结果"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-execution")
async def analyze_execution_results(request: ExecutionAnalysisRequest):
    """AI分析执行结果"""
    try:
        execution_results = request.execution_results
        logger.info("AI开始分析执行结果...")

        # 构建分析上下文
        context = {
            "execution_summary": {
                "total_commands": len(execution_results.get('commands', [])),
                "successful_commands": len([cmd for cmd in execution_results.get('commands', []) if cmd.get('success', False)]),
                "total_time": execution_results.get('total_time', 0),
                "overall_success": execution_results.get('success', False)
            },
            "detailed_results": execution_results.get('commands', [])
        }

        # 使用系统分析器进行AI分析
        analyzer = SystemAnalyzer()

        # 构建执行结果分析提示
        analysis_prompt = f"""
请分析以下系统修复方案的执行结果，并根据实际找到的进程信息，生成精准的后续修复方案：

## 执行总结
- 总命令数: {context['execution_summary']['total_commands']}
- 成功命令数: {context['execution_summary']['successful_commands']}
- 总执行时间: {context['execution_summary']['total_time']}秒
- 整体状态: {'成功' if context['execution_summary']['overall_success'] else '部分失败'}

## 详细执行结果
{json.dumps(context['detailed_results'], ensure_ascii=False, indent=2)}

## 重要：智能命令生成要求
请仔细分析执行结果中的命令输出，特别是：
1. 如果包含进程列表（如ps、top命令的输出），请提取出占用CPU或内存最高的具体进程PID
2. 如果发现了具体的进程PID，请在后续修复方案中使用真实的PID，而不是示例PID（如1234）
3. 基于实际发现的进程信息，生成具体的kill命令或其他修复命令

请基于以上执行结果提供：
1. 执行结果分析
2. 系统状态改善评估
3. 发现的新问题（如果有）
4. 从执行结果中提取的关键进程信息
5. 后续建议操作
6. 是否需要进一步修复

请按以下JSON格式回复：
{{
    "execution_analysis": "执行结果总体分析",
    "system_improvement": "系统状态改善情况",
    "detected_processes": [
        {{
            "pid": "进程ID",
            "command": "进程命令",
            "cpu_usage": "CPU使用率",
            "memory_usage": "内存使用率",
            "description": "进程描述"
        }}
    ],
    "new_issues": ["发现的新问题1", "发现的新问题2"],
    "next_steps": ["后续建议步骤1", "后续建议步骤2"],
    "requires_further_action": true|false,
    "fix_plans": [
        {{
            "id": "followup_plan_1",
            "issue": "基于实际进程的后续修复",
            "description": "根据执行结果发现的具体进程信息生成的修复方案",
            "priority": "high|medium|low",
            "commands": [
                {{
                    "step": 1,
                    "description": "执行步骤描述（必须包含实际PID）",
                    "command": "使用真实PID的具体命令，如kill -9 [实际PID]",
                    "expected_output": "预期输出",
                    "timeout": 30
                }}
            ],
            "risk_level": "low|medium|high",
            "estimated_time": "预估执行时间（分钟）",
            "preconditions": ["确认进程PID正确", "确认不会影响关键服务"],
            "verification_commands": []
        }}
    ]
}}

**重要提醒：**
- 必须从执行结果的输出中提取真实的进程PID
- 后续修复方案中的命令必须使用实际的PID，不能用占位符
- 如果没有找到需要处理的进程，请在fix_plans中提供空数组
"""

        # 调用LLM进行分析
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=analyzer.system_prompt),
            HumanMessage(content=analysis_prompt)
        ]

        response = analyzer.llm.invoke(messages)
        analysis_text = response.content

        # 解析分析结果
        parsed_result = analyzer._parse_analysis_result(analysis_text)

        return {
            "success": True,
            "analysis": parsed_result,
            "raw_analysis": analysis_text,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"AI分析执行结果失败: {e}")
        return {
            "success": False,
            "error": f"AI分析执行结果失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/save-fix-plans")
async def save_fix_plans(request: SaveFixPlansRequest):
    """保存修复方案到状态管理器"""
    try:
        fix_plans = request.fix_plans

        # 保存到状态管理器
        ops_assistant.state_manager.set_fix_plans(fix_plans)

        # 保存到全局变量
        global last_execution_results
        if last_execution_results:
            last_execution_results['new_fix_plans'] = fix_plans

        logger.info(f"保存了 {len(fix_plans)} 个修复方案到状态管理器")

        return {
            "success": True,
            "message": f"成功保存 {len(fix_plans)} 个修复方案",
            "count": len(fix_plans)
        }

    except Exception as e:
        logger.error(f"保存修复方案失败: {e}")
        return {
            "success": False,
            "error": f"保存修复方案失败: {str(e)}"
        }

@app.post("/api/command/edit")
async def edit_command(request: CommandEditRequest):
    """编辑修复方案中的命令"""
    try:
        plan_id = request.plan_id
        command_index = request.command_index
        new_command = request.new_command.strip()

        logger.info(f"用户编辑命令: 方案ID={plan_id}, 命令索引={command_index}, 新命令={new_command[:50]}...")

        # 验证命令安全性
        if not _validate_command_security(new_command):
            return {
                "success": False,
                "error": "命令验证失败",
                "message": "命令包含不安全的内容，请检查后重试"
            }

        # 获取当前状态和修复方案
        state = ops_assistant.get_current_state()
        fix_plans = state.get('fix_plans', [])

        # 查找指定的修复方案
        selected_plan = None
        plan_index = None

        for i, plan in enumerate(fix_plans):
            if plan.get('id') == plan_id or f"plan_{i+1}" == plan_id:
                selected_plan = plan
                plan_index = i
                break

        if not selected_plan:
            # 如果没找到，尝试从其他数据源查找
            current_fix_plans = ops_assistant.state_manager.state.get('fix_plans', [])
            for i, plan in enumerate(current_fix_plans):
                if plan.get('id') == plan_id or f"plan_{i+1}" == plan_id:
                    selected_plan = plan
                    plan_index = i
                    fix_plans = current_fix_plans
                    break

        if not selected_plan or plan_index is None:
            return {
                "success": False,
                "error": "方案未找到",
                "message": f"未找到修复方案: {plan_id}"
            }

        # 检查命令索引
        commands = selected_plan.get('commands', [])
        if not commands or command_index < 0 or command_index >= len(commands):
            return {
                "success": False,
                "error": "命令索引无效",
                "message": f"无效的命令索引: {command_index}"
            }

        # 保存原始命令（如果尚未保存）
        if not commands[command_index].get('original_command'):
            commands[command_index]['original_command'] = commands[command_index]['command']

        # 更新命令
        commands[command_index]['command'] = new_command
        commands[command_index]['user_modified'] = True
        commands[command_index]['modified_at'] = datetime.now().isoformat()

        # 更新状态
        fix_plans[plan_index]['commands'] = commands
        ops_assistant.state_manager.set_fix_plans(fix_plans)

        # 记录编辑操作
        ops_assistant.state_manager.add_action("edit_command", {
            "plan_id": plan_id,
            "command_index": command_index,
            "original_command": request.original_command or commands[command_index]['original_command'],
            "new_command": new_command,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"成功编辑命令: {plan_id}[{command_index}]")

        return {
            "success": True,
            "message": "命令编辑成功",
            "plan_id": plan_id,
            "command_index": command_index,
            "new_command": new_command
        }

    except Exception as e:
        logger.error(f"编辑命令失败: {str(e)}")
        return {
            "success": False,
            "error": "编辑失败",
            "message": f"编辑命令时发生错误: {str(e)}"
        }

def _validate_command_security(command: str) -> bool:
    """验证命令安全性"""
    if not command or len(command.strip()) == 0:
        return False

    # 导入正则表达式
    import re

    # 转换为小写进行检查
    lower_command = command.lower()

    # 危险命令模式
    dangerous_patterns = [
        r'rm\s+-rf\s+/',  # rm -rf /
        r'dd\s+if=',      # dd命令（可能破坏磁盘）
        r'mkfs\.',        # 文件系统格式化
        r'format',        # 格式化命令
        r'shutdown\s+-h', # 关机命令
        r'reboot',        # 重启命令
        r'halt',          # 停机命令
        r'poweroff',      # 关机命令
        r'>\s*/dev/sda',  # 直接写入硬盘
        r'dd\s+if.*of.*/dev/sd', # 直接写入硬盘分区
        r'curl.*\|\s*sh', # 下载并执行脚本
        r'wget.*\|\s*bash', # 下载并执行脚本
        r'eval\s*\(',     # eval函数
        r'exec\s*\(',     # exec函数
        r'system\s*\(',   # system函数
        r'chmod\s+777\s+/', # 危险的权限设置
        r'chmod\s+777\s+\*', # 危险的权限设置
        r'chown\s+-R\s+root\s+/', # 危险的所有权变更
        r':\(\)\{\.*\;\}\s*\/dev\/null&', # fork炸弹模式
        r'sudo\s+rm\s+-rf\s+/', # 危险的sudo删除
        r'su\s+root\s+-c\s*rm', # 危险的root删除
    ]

    # 检查危险模式
    for pattern in dangerous_patterns:
        if re.search(pattern, lower_command):
            logger.warning(f"检测到危险命令模式: {pattern} in {command}")
            return False

    # 检查是否包含可疑的字符组合
    suspicious_chars = ['&& rm -rf', '; rm -rf', '| rm -rf', '`rm -rf`', '$(rm -rf)']
    for suspicious in suspicious_chars:
        if suspicious in lower_command:
            logger.warning(f"检测到可疑字符组合: {suspicious}")
            return False

    return True

# 全局变量存储最后执行结果
last_execution_results = None

# WebSocket端点
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 这里可以处理前端发送的消息
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    print("[STARTUP] 智能运维助手Web服务启动成功!")
    print(f"[MONITOR] 监控目标: {Config.SERVER_HOST}")
    print(f"[PROMETHEUS] Prometheus: {Config.PROMETHEUS_URL}")
    print(f"[AI] AI模型: {Config.LLM_MODEL}")

if __name__ == "__main__":
    uvicorn.run(
        "web_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )