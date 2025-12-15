#!/usr/bin/env python3
"""
RAG (Retrieval-Augmented Generation) 引擎
将向量检索集成到对话工作流中
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate

from vector_database import get_vector_database
from config import Config
from logger_config import get_logger, log_operation, log_performance

logger = get_logger(__name__)


class RAGEngine:
    """检索增强生成引擎"""

    def __init__(self):
        self.llm = ChatOpenAI(
            base_url=Config.LLM_BASE_URL,
            api_key=Config.DASHSCOPE_API_KEY,
            model=Config.LLM_MODEL,
            temperature=0.1
        )
        self.vector_db = get_vector_database()

        # RAG提示词模板
        self.rag_prompt_template = PromptTemplate(
            input_variables=["context", "question", "chat_history"],
            template="""你是一个专业的智能运维助手。请基于以下知识库内容和用户问题提供准确、详细的回答。

## 知识库内容
{context}

## 用户问题
{question}

## 对话历史
{chat_history}

## 回答要求
1. 请主要基于知识库内容回答问题
2. 如果知识库中没有相关信息，请明确说明
3. 可以结合你的专业知识进行补充和解释
4. 回答要条理清晰、重点突出
5. 如果涉及技术操作，请提供具体步骤

## 回答
"""
        )

    def should_use_rag(self, message: str) -> bool:
        """判断是否应该使用RAG"""
        # 简单的关键词匹配来判断是否需要知识库检索
        rag_keywords = [
            "如何", "怎么", "怎样", "什么是", "解释", "说明", "介绍",
            "原理", "配置", "安装", "部署", "优化", "故障", "问题",
            "错误", "解决", "方法", "步骤", "教程", "文档", "手册"
        ]

        message_lower = message.lower()
        return any(keyword in message_lower for keyword in rag_keywords)

    def retrieve_relevant_context(self, query: str, k: int = 5) -> Dict[str, Any]:
        """检索相关上下文"""
        try:
            search_result = self.vector_db.search_with_context(query, k)
            return search_result
        except Exception as e:
            logger.error(f"检索上下文失败: {e}")
            return {
                "context": "",
                "sources": [],
                "total_results": 0,
                "error": str(e)
            }

    def format_chat_history(self, history: List[Dict[str, Any]] = None) -> str:
        """格式化对话历史"""
        if not history:
            return "无历史对话"

        formatted_history = []
        for i, msg in enumerate(history[-5:]):  # 只保留最近5轮对话
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")
            formatted_history.append(f"{role}: {content}")

        return "\n".join(formatted_history)

    def generate_with_rag(self,
                         message: str,
                         chat_history: List[Dict[str, Any]] = None,
                         k: int = 5) -> Dict[str, Any]:
        """使用RAG生成回答"""
        try:
            log_operation("开始RAG生成", {
                "message_length": len(message),
                "history_count": len(chat_history) if chat_history else 0
            })

            # 1. 检索相关上下文
            search_result = self.retrieve_relevant_context(message, k)
            context = search_result.get("context", "")
            sources = search_result.get("sources", [])

            # 2. 格式化对话历史
            formatted_history = self.format_chat_history(chat_history)

            # 3. 构建提示词
            prompt = self.rag_prompt_template.format(
                context=context if context else "知识库中没有找到直接相关的内容",
                question=message,
                chat_history=formatted_history
            )

            # 4. 生成回答
            messages = [
                SystemMessage(content="你是一个专业的智能运维助手，擅长基于知识库内容回答用户的技术问题。"),
                HumanMessage(content=prompt)
            ]

            response = self.llm.invoke(messages)
            answer = response.content

            # 5. 构建结果
            result = {
                "success": True,
                "answer": answer,
                "sources": sources,
                "context_used": bool(context),
                "retrieval_results": search_result.get("total_results", 0),
                "rag_used": True,
                "timestamp": datetime.now().isoformat()
            }

            log_operation("RAG生成完成", {
                "answer_length": len(answer),
                "sources_count": len(sources),
                "context_used": result["context_used"]
            })

            return result

        except Exception as e:
            logger.error(f"RAG生成失败: {e}")
            return {
                "success": False,
                "answer": f"抱歉，在检索知识库时遇到错误: {str(e)}",
                "sources": [],
                "context_used": False,
                "retrieval_results": 0,
                "rag_used": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def generate_without_rag(self,
                           message: str,
                           chat_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """不使用RAG直接生成回答"""
        try:
            formatted_history = self.format_chat_history(chat_history)

            prompt = f"""用户问题: {message}

对话历史:
{formatted_history}

请直接回答用户的问题，不需要参考知识库。"""

            messages = [
                SystemMessage(content="你是一个智能运维助手，可以回答各种运维相关问题。"),
                HumanMessage(content=prompt)
            ]

            response = self.llm.invoke(messages)
            answer = response.content

            return {
                "success": True,
                "answer": answer,
                "sources": [],
                "context_used": False,
                "retrieval_results": 0,
                "rag_used": False,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"直接生成失败: {e}")
            return {
                "success": False,
                "answer": f"抱歉，处理您的问题时遇到错误: {str(e)}",
                "sources": [],
                "context_used": False,
                "retrieval_results": 0,
                "rag_used": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def process_message(self,
                       message: str,
                       use_rag: bool = None,
                       chat_history: List[Dict[str, Any]] = None,
                       force_rag: bool = False) -> Dict[str, Any]:
        """处理消息 - 主入口"""
        try:
            # 确定是否使用RAG
            if force_rag:
                rag_enabled = True
            elif use_rag is not None:
                rag_enabled = use_rag
            else:
                rag_enabled = self.should_use_rag(message)

            log_operation("消息处理开始", {
                "message_length": len(message),
                "rag_enabled": rag_enabled,
                "force_rag": force_rag
            })

            if rag_enabled:
                return self.generate_with_rag(message, chat_history)
            else:
                return self.generate_without_rag(message, chat_history)

        except Exception as e:
            logger.error(f"消息处理失败: {e}")
            return {
                "success": False,
                "answer": f"抱歉，处理消息时遇到错误: {str(e)}",
                "sources": [],
                "context_used": False,
                "retrieval_results": 0,
                "rag_used": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# 全局RAG引擎实例
rag_engine = None


def get_rag_engine() -> RAGEngine:
    """获取RAG引擎实例"""
    global rag_engine
    if rag_engine is None:
        rag_engine = RAGEngine()
    return rag_engine