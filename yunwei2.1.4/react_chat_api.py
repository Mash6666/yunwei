#!/usr/bin/env python3
"""
React机制的聊天API
替换原有的聊天API，使用智能路由和React工作流
"""

from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException
from pydantic import BaseModel

from react_ops_graph import ReactOpsAssistantGraph
from rag_engine import get_rag_engine
from logger_config import get_logger, error_logger, async_error_logger, log_operation, log_performance
from langgraph_logger import langgraph_logger

logger = get_logger(__name__)

class ChatRequest(BaseModel):
    message: str
    use_knowledge_base: bool = False

class ReactChatHandler:
    """React聊天处理器"""

    def __init__(self):
        self.ops_assistant = ReactOpsAssistantGraph()
        self.rag_engine = get_rag_engine()

    @async_error_logger(context="React聊天API")
    async def handle_chat(self, message: str, use_knowledge_base: bool = False) -> Dict[str, Any]:
        """处理聊天请求"""
        import time
        start_time = time.time()

        try:
            if not message.strip():
                return {
                    "success": False,
                    "response": "请输入你的问题"
                }

            # 记录用户查询
            log_operation("用户发送React聊天消息", {
                "message_length": len(message),
                "message_preview": message[:50] + "..." if len(message) > 50 else message,
                "use_knowledge_base": use_knowledge_base
            }, user="web_client")

            # 如果启用知识库检索，使用RAG引擎
            if use_knowledge_base:
                log_operation("使用RAG引擎处理消息", {"message": message[:100]}, user="web_client")

                # 使用RAG引擎处理消息
                rag_result = self.rag_engine.process_message(
                    message=message.strip(),
                    force_rag=True
                )

                if rag_result["success"]:
                    # 记录性能
                    end_time = time.time()
                    processing_time = end_time - start_time
                    log_performance("rag_chat_api", start_time, end_time, {
                        "message_length": len(message),
                        "response_length": len(rag_result.get("answer", "")),
                        "context_used": rag_result.get("context_used", False),
                        "retrieval_results": rag_result.get("retrieval_results", 0)
                    })

                    log_operation("RAG聊天完成", {
                        "processing_time": f"{processing_time:.2f}s",
                        "response_length": len(rag_result.get("answer", "")),
                        "context_used": rag_result.get("context_used", False),
                        "retrieval_results": rag_result.get("retrieval_results", 0)
                    }, user="web_client")

                    return {
                        "success": True,
                        "response": rag_result.get("answer", ""),
                        "timestamp": rag_result.get("timestamp", datetime.now().isoformat()),
                        "processing_time": processing_time,
                        "rag_used": True,
                        "context_used": rag_result.get("context_used", False),
                        "sources": rag_result.get("sources", []),
                        "retrieval_results": rag_result.get("retrieval_results", 0),
                        "workflow_type": "rag",
                        "response_type": "knowledge_base"
                    }
                else:
                    # RAG失败，回退到React工作流
                    log_operation("RAG处理失败，回退到React工作流", {
                        "error": rag_result.get("error", "未知错误")
                    }, level="warning", user="web_client")

            # 使用React智能运维助手处理请求
            result = await self.ops_assistant.run(message.strip())

            if result["success"]:
                # 记录性能和操作完成
                end_time = time.time()
                processing_time = end_time - start_time
                log_performance("react_chat_api", start_time, end_time, {
                    "message_length": len(message),
                    "response_length": len(result.get("response", "")),
                    "workflow_type": result.get("workflow_type", "unknown"),
                    "response_type": result.get("response_type", "unknown")
                })

                log_operation("React聊天完成", {
                    "processing_time": f"{processing_time:.2f}s",
                    "response_length": len(result.get("response", "")),
                    "session_id": result.get("session_id"),
                    "workflow_type": result.get("workflow_type"),
                    "response_type": result.get("response_type")
                }, user="web_client")

                return {
                    "success": True,
                    "response": result.get("response", ""),
                    "timestamp": datetime.now().isoformat(),
                    "processing_time": processing_time,
                    "session_id": result.get("session_id"),
                    "workflow_type": result.get("workflow_type"),
                    "response_type": result.get("response_type"),
                    "system_performed_check": result.get("workflow_type") == "system_check",
                    "summary": result.get("summary", {}),
                    "rag_used": False,
                    "context_used": False,
                    "sources": [],
                    "retrieval_results": 0
                }
            else:
                # 处理失败情况
                log_operation("React聊天失败", {
                    "error": result.get("error", "未知错误"),
                    "processing_time": f"{processing_time:.2f}s"
                }, level="error", user="web_client")

                return {
                    "success": False,
                    "error": result.get("error", "处理请求时发生未知错误"),
                    "response": result.get("response", "抱歉，处理您的问题时遇到了错误。"),
                    "timestamp": datetime.now().isoformat(),
                    "rag_used": False,
                    "context_used": False,
                    "sources": [],
                    "retrieval_results": 0
                }

        except Exception as e:
            end_time = time.time()
            processing_time = end_time - start_time

            log_operation("React聊天API异常", {
                "error": str(e),
                "processing_time": f"{processing_time:.2f}s"
            }, level="error", user="web_client")

            return {
                "success": False,
                "error": str(e),
                "response": "抱歉，系统遇到了异常。请稍后重试。",
                "timestamp": datetime.now().isoformat(),
                "rag_used": False,
                "context_used": False,
                "sources": [],
                "retrieval_results": 0
            }


# 全局处理器实例
react_chat_handler = ReactChatHandler()