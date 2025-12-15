#!/usr/bin/env python3
"""
LangGraph过程日志记录模块
专门用于记录LangGraph工作流中的用户交互、AI回复和节点执行过程
"""

import json
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path

from logger_config import get_logger, log_operation, log_performance, ErrorTracker


@dataclass
class ConversationLog:
    """对话日志记录"""
    timestamp: str
    session_id: str
    user_query: str
    query_hash: str
    ai_response: str
    response_hash: str
    query_length: int
    response_length: int
    processing_time: float
    node_sequence: List[str]
    success: bool
    error_message: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None


@dataclass
class NodeExecutionLog:
    """节点执行日志记录"""
    timestamp: str
    session_id: str
    node_name: str
    start_time: float
    end_time: float
    execution_time: float
    input_state: Dict[str, Any]
    output_state: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class StateTransitionLog:
    """状态转换日志记录"""
    timestamp: str
    session_id: str
    from_node: str
    to_node: str
    transition_condition: str
    state_snapshot: Dict[str, Any]


class LangGraphLogger:
    """LangGraph专用日志记录器"""

    def __init__(self, log_dir: str = "logs"):
        self.logger = get_logger("langgraph")
        self.error_tracker = ErrorTracker(self.logger)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # 专门的日志文件
        self.conversation_log_file = self.log_dir / "langgraph_conversations.log"
        self.node_execution_log_file = self.log_dir / "langgraph_nodes.log"
        self.state_transition_log_file = self.log_dir / "langgraph_transitions.log"

        # 内存中的日志缓存
        self.current_session: Optional[str] = None
        self.node_stack: List[str] = []
        self.session_start_time: Optional[float] = None

    def start_session(self, session_id: str, user_query: str = ""):
        """开始新的会话"""
        self.current_session = session_id
        self.session_start_time = time.time()
        self.node_stack = []

        self.logger.info(f"开始新会话: {session_id}")
        if user_query:
            self.logger.info(f"用户查询: {user_query[:100]}{'...' if len(user_query) > 100 else ''}")

    def end_session(self):
        """结束会话"""
        if self.current_session and self.session_start_time:
            session_time = time.time() - self.session_start_time
            self.logger.info(f"会话结束: {self.current_session}, 总耗时: {session_time:.2f}s")

        self.current_session = None
        self.node_stack = []
        self.session_start_time = None

    def log_node_start(self, node_name: str, state: Dict[str, Any]):
        """记录节点开始执行"""
        if not self.current_session:
            self.logger.warning("尝试记录节点执行但没有活动会话")
            return

        start_time = time.time()
        self.node_stack.append(node_name)

        # 记录节点开始
        self.logger.info(f"开始执行节点: {node_name} (会话: {self.current_session})")

        # 将开始时间存入状态中，供后续记录使用
        state["_log_start_time"] = start_time
        state["_log_node_name"] = node_name

        # 记录状态快照（简化版本，避免过大）
        state_snapshot = self._create_state_snapshot(state)
        self.logger.debug(f"节点 {node_name} 输入状态快照: {json.dumps(state_snapshot, ensure_ascii=False)[:500]}")

    def log_node_end(self, node_name: str, input_state: Dict[str, Any], output_state: Dict[str, Any],
                    success: bool = True, error_message: str = None, metadata: Dict[str, Any] = None):
        """记录节点执行结束"""
        if not self.current_session:
            return

        start_time = input_state.get("_log_start_time", time.time())
        end_time = time.time()
        execution_time = end_time - start_time

        # 创建节点执行日志
        node_log = NodeExecutionLog(
            timestamp=datetime.now().isoformat(),
            session_id=self.current_session,
            node_name=node_name,
            start_time=start_time,
            end_time=end_time,
            execution_time=execution_time,
            input_state=self._create_state_snapshot(input_state),
            output_state=self._create_state_snapshot(output_state),
            success=success,
            error_message=error_message,
            metadata=metadata or {}
        )

        # 记录到日志文件
        self._write_node_log(node_log)

        # 记录到标准日志
        if success:
            self.logger.info(f"节点执行成功: {node_name} (耗时: {execution_time:.2f}s)")
        else:
            self.logger.error(f"节点执行失败: {node_name} (耗时: {execution_time:.2f}s), 错误: {error_message}")

        # 记录性能指标
        log_performance(f"langgraph_node_{node_name}", start_time, end_time, {
            "session_id": self.current_session,
            "node_name": node_name,
            "success": success,
            "metadata": metadata or {}
        })

        # 从堆栈中移除节点
        if node_name in self.node_stack:
            self.node_stack.remove(node_name)

    def log_state_transition(self, from_node: str, to_node: str, condition: str, state: Dict[str, Any]):
        """记录状态转换"""
        if not self.current_session:
            return

        transition_log = StateTransitionLog(
            timestamp=datetime.now().isoformat(),
            session_id=self.current_session,
            from_node=from_node,
            to_node=to_node,
            transition_condition=condition,
            state_snapshot=self._create_state_snapshot(state)
        )

        # 记录到日志文件
        self._write_transition_log(transition_log)

        # 记录到标准日志
        self.logger.info(f"状态转换: {from_node} -> {to_node} (条件: {condition})")

    def log_conversation(self, user_query: str, ai_response: str, node_sequence: List[str],
                        success: bool = True, error_message: str = None,
                        context_data: Dict[str, Any] = None):
        """记录完整的对话"""
        if not self.current_session:
            self.current_session = f"session_{int(time.time())}"

        processing_time = time.time() - self.session_start_time if self.session_start_time else 0

        # 创建对话日志
        conversation_log = ConversationLog(
            timestamp=datetime.now().isoformat(),
            session_id=self.current_session,
            user_query=user_query,
            query_hash=self._hash_text(user_query),
            ai_response=ai_response,
            response_hash=self._hash_text(ai_response),
            query_length=len(user_query),
            response_length=len(ai_response),
            processing_time=processing_time,
            node_sequence=node_sequence.copy(),
            success=success,
            error_message=error_message,
            context_data=context_data
        )

        # 记录到日志文件
        self._write_conversation_log(conversation_log)

        # 记录到标准日志
        log_operation("LangGraph对话完成", {
            "session_id": self.current_session,
            "query_length": len(user_query),
            "response_length": len(ai_response),
            "processing_time": f"{processing_time:.2f}s",
            "node_sequence": "->".join(node_sequence),
            "success": success
        }, user="langgraph_user")

        # 记录用户查询和AI回复
        self.logger.info(f"用户查询: {user_query[:200]}{'...' if len(user_query) > 200 else ''}")
        self.logger.info(f"AI回复: {ai_response[:200]}{'...' if len(ai_response) > 200 else ''}")

    def log_llm_interaction(self, phase: str, prompt: str, response: str, tokens_used: int = None,
                           model_name: str = None, response_time: float = None):
        """记录与LLM的交互"""
        self.logger.info(f"LLM交互 - {phase}")

        # 记录提示词和响应的摘要
        prompt_summary = prompt[:300] + "..." if len(prompt) > 300 else prompt
        response_summary = response[:300] + "..." if len(response) > 300 else response

        self.logger.debug(f"LLM提示词: {prompt_summary}")
        self.logger.debug(f"LLM响应: {response_summary}")

        # 记录元数据
        metadata = {
            "phase": phase,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "session_id": self.current_session
        }

        if tokens_used:
            metadata["tokens_used"] = tokens_used
        if model_name:
            metadata["model_name"] = model_name
        if response_time:
            metadata["response_time"] = f"{response_time:.2f}s"

        log_operation("LLM交互", metadata, user="system")

    def log_system_action(self, action_name: str, parameters: Dict[str, Any], result: Any = None,
                         success: bool = True, error_message: str = None):
        """记录系统操作"""
        log_data = {
            "action": action_name,
            "parameters": parameters,
            "session_id": self.current_session
        }

        if result is not None:
            if isinstance(result, (dict, list)):
                log_data["result"] = {"type": type(result).__name__, "size": len(result)}
            else:
                log_data["result"] = {"type": type(result).__name__, "value": str(result)[:100]}

        if success:
            self.logger.info(f"系统操作成功: {action_name}")
            log_operation(f"系统操作: {action_name}", log_data, user="system")
        else:
            self.logger.error(f"系统操作失败: {action_name}, 错误: {error_message}")
            log_operation(f"系统操作失败: {action_name}", {**log_data, "error": error_message}, level="error")

    def _create_state_snapshot(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """创建状态快照，去除敏感信息和过大数据"""
        if not isinstance(state, dict):
            return {"type": type(state).__name__, "value": str(state)[:100]}

        snapshot = {}
        sensitive_keys = ["password", "token", "key", "secret", "credential"]

        for key, value in state.items():
            # 跳过内部日志字段
            if key.startswith("_log_"):
                continue

            # 检查敏感字段
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                snapshot[key] = "[REDACTED]"
                continue

            # 处理不同类型的值
            if isinstance(value, (str, int, float, bool)):
                if isinstance(value, str) and len(value) > 200:
                    snapshot[key] = value[:200] + "..."
                else:
                    snapshot[key] = value
            elif isinstance(value, (list, tuple)):
                snapshot[key] = f"List/Tuple with {len(value)} items"
            elif isinstance(value, dict):
                snapshot[key] = f"Dict with {len(value)} keys"
            elif hasattr(value, '__dict__'):
                snapshot[key] = f"Object: {type(value).__name__}"
            else:
                snapshot[key] = str(value)[:100]

        return snapshot

    def _hash_text(self, text: str) -> str:
        """为文本生成哈希值"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

    def _write_conversation_log(self, log: ConversationLog):
        """写入对话日志到文件"""
        try:
            log_dict = asdict(log)
            # 处理不可序列化的对象
            if 'context_data' in log_dict and log_dict['context_data']:
                context_data = log_dict['context_data']
                if 'system_status' in context_data:
                    context_data['system_status'] = str(context_data['system_status'])
                log_dict['context_data'] = context_data

            log_entry = f"{json.dumps(log_dict, ensure_ascii=False)}\n"
            with open(self.conversation_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            self.logger.error(f"写入对话日志失败: {e}")

    def _write_node_log(self, log: NodeExecutionLog):
        """写入节点执行日志到文件"""
        try:
            log_entry = f"{json.dumps(asdict(log), ensure_ascii=False)}\n"
            with open(self.node_execution_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            self.logger.error(f"写入节点日志失败: {e}")

    def _write_transition_log(self, log: StateTransitionLog):
        """写入状态转换日志到文件"""
        try:
            log_entry = f"{json.dumps(asdict(log), ensure_ascii=False)}\n"
            with open(self.state_transition_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            self.logger.error(f"写入转换日志失败: {e}")


# 全局LangGraph日志记录器实例
langgraph_logger = LangGraphLogger()


def log_langgraph_node(node_name: str):
    """LangGraph节点装饰器，自动记录节点执行"""
    def decorator(func):
        async def async_wrapper(self, state, *args, **kwargs):
            # 记录节点开始
            langgraph_logger.log_node_start(node_name, state)

            try:
                # 执行节点函数
                result = await func(self, state, *args, **kwargs)

                # 记录节点成功完成
                langgraph_logger.log_node_end(
                    node_name, state, result, success=True
                )

                return result

            except Exception as e:
                # 记录节点执行失败
                langgraph_logger.log_node_end(
                    node_name, state, state, success=False, error_message=str(e)
                )
                raise

        def sync_wrapper(self, state, *args, **kwargs):
            # 记录节点开始
            langgraph_logger.log_node_start(node_name, state)

            try:
                # 执行节点函数
                result = func(self, state, *args, **kwargs)

                # 记录节点成功完成
                langgraph_logger.log_node_end(
                    node_name, state, result, success=True
                )

                return result

            except Exception as e:
                # 记录节点执行失败
                langgraph_logger.log_node_end(
                    node_name, state, state, success=False, error_message=str(e)
                )
                raise

        # 根据函数类型返回相应的包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_langgraph_transition(from_node: str, condition: str = "default"):
    """记录状态转换的装饰器"""
    def decorator(func):
        def wrapper(self, state, *args, **kwargs):
            # 执行条件判断函数
            result = func(self, state, *args, **kwargs)

            # 记录状态转换
            langgraph_logger.log_state_transition(
                from_node, result, condition, state
            )

            return result
        return wrapper
    return decorator