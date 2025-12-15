#!/usr/bin/env python3
"""
简单的自然语言数据库查询器
使用Function Calling实现，普通对话直接用大模型
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from database_manager import db_manager
from logger_config import get_logger

logger = get_logger(__name__)

@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # user, assistant, system
    content: str
    timestamp: float = None

class SimpleDatabaseChat:
    """简单的自然语言数据库查询器"""

    def __init__(self):
        self.llm = None  # 将在web_app中设置
        self.conversation_history: List[ChatMessage] = []
        self._setup_tools()

    def set_llm(self, llm):
        """设置LLM"""
        self.llm = llm

    def _setup_tools(self):
        """设置Function Calling工具"""

        @tool
        def list_databases():
            """获取所有数据库列表"""
            try:
                databases = db_manager.get_databases()
                return {
                    "success": True,
                    "data": databases,
                    "count": len(databases)
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }

        @tool
        def list_tables(database: str):
            """获取指定数据库中的所有表

            Args:
                database: 数据库名称
            """
            try:
                tables = db_manager.get_tables(database)
                return {
                    "success": True,
                    "data": tables,
                    "database": database,
                    "count": len(tables)
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "database": database
                }

        @tool
        def get_table_structure(database: str, table: str):
            """获取表的结构信息

            Args:
                database: 数据库名称
                table: 表名
            """
            try:
                structure = db_manager.get_table_structure(database, table)
                return {
                    "success": True,
                    "data": structure,
                    "database": database,
                    "table": table,
                    "column_count": len(structure)
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "database": database,
                    "table": table
                }

        @tool
        def count_records(database: str, table: str):
            """统计表中的记录数

            Args:
                database: 数据库名称
                table: 表名
            """
            try:
                result = db_manager.execute_query(database, f"SELECT COUNT(*) as total FROM `{table}`")
                return result
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "database": database,
                    "table": table
                }

        @tool
        def query_table_data(database: str, table: str, limit: int = 10):
            """查询表中的数据

            Args:
                database: 数据库名称
                table: 表名
                limit: 返回记录数限制，默认10条
            """
            try:
                result = db_manager.execute_query(database, f"SELECT * FROM `{table}` LIMIT {limit}")
                return result
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "database": database,
                    "table": table
                }

        @tool
        def execute_safe_query(database: str, query: str):
            """执行安全的SELECT查询

            Args:
                database: 数据库名称
                query: SQL查询语句（仅限SELECT）
            """
            try:
                # 安全检查
                if not query.strip().upper().startswith('SELECT'):
                    return {
                        "success": False,
                        "error": "出于安全考虑，只允许执行SELECT查询"
                    }

                result = db_manager.execute_query(database, query)
                return result
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "database": database,
                    "query": query
                }

        self.tools = [
            list_databases,
            list_tables,
            get_table_structure,
            count_records,
            query_table_data,
            execute_safe_query
        ]

    def _is_database_query(self, message: str) -> bool:
        """判断是否是数据库相关查询"""
        message_lower = message.lower()
        db_keywords = [
            '数据库', '表', '查询', '数据', '记录', '字段', '结构',
            'database', 'table', 'query', 'data', 'record', 'field', 'schema',
            'select', 'show', 'describe', 'count', 'list'
        ]
        return any(keyword in message_lower for keyword in db_keywords)

    async def chat(self, message: str, database: str = None, table: str = None) -> Dict[str, Any]:
        """聊天处理"""
        logger.info(f"🤖 收到用户对话请求 - 上下文: 数据库={database}, 表={table}")
        logger.debug(f"用户消息: {message}")

        start_time = asyncio.get_event_loop().time()

        try:
            # 添加用户消息到历史记录
            self.conversation_history.append(ChatMessage(role="user", content=message))
            logger.debug(f"对话历史长度: {len(self.conversation_history)}")

            # 判断是否是数据库查询
            if self._is_database_query(message):
                # 数据库查询：使用Function Calling
                system_prompt = f"""你是一个数据库助手，可以帮助用户查询数据库信息。

当前上下文：
- 数据库：{database or '未选择'}
- 表：{table or '未选择'}

你可以使用以下工具来帮助用户：
1. list_databases - 获取所有数据库
2. list_tables - 获取数据库中的表
3. get_table_structure - 获取表结构
4. count_records - 统计记录数
5. query_table_data - 查询表数据
6. execute_safe_query - 执行安全的SELECT查询

重要规则：
- 只执行SELECT查询，不执行任何修改性操作
- 如果用户没有指定具体的数据库或表，引导他们选择
- 用自然语言解释查询结果
- 如果查询失败，提供有用的错误信息

请根据用户的请求选择合适的工具来获取数据，然后用自然语言回答用户的问题。"""

                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=message)
                ]

                # 绑定工具到LLM
                llm_with_tools = self.llm.bind_tools(self.tools)

                # 调用LLM
                response = await llm_with_tools.ainvoke(messages)

                # 如果LLM决定使用工具
                if response.tool_calls:
                    tool_results = []

                    # 执行工具调用
                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]

                        # 找到对应的工具
                        tool_func = next((t for t in self.tools if t.name == tool_name), None)
                        if tool_func:
                            try:
                                result = tool_func.invoke(tool_args)
                                tool_results.append({
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "result": result
                                })
                            except Exception as e:
                                tool_results.append({
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "result": {"success": False, "error": str(e)}
                                })

                    # 生成最终响应
                    if tool_results:
                        # 将工具结果格式化为文本
                        results_text = ""
                        for i, tr in enumerate(tool_results, 1):
                            results_text += f"\n工具{i}: {tr['tool']}\n"
                            results_text += f"参数: {tr['args']}\n"
                            results_text += f"结果: {tr['result']}\n"

                        # 让LLM根据工具结果生成自然语言回复
                        final_messages = [
                            SystemMessage(content=system_prompt),
                            HumanMessage(content=message),
                            AIMessage(content=f"我已经执行了相关查询，结果如下：{results_text}"),
                            HumanMessage(content="请根据以上查询结果，用自然语言回答我的原始问题。")
                        ]

                        final_response = await self.llm.ainvoke(final_messages)
                        chat_response = final_response.content

                        # 获取第一个成功的结果作为sql_result
                        sql_result = None
                        for tr in tool_results:
                            if tr["result"].get("success"):
                                sql_result = tr["result"]
                                break

                        if not sql_result and tool_results:
                            sql_result = tool_results[0]["result"]
                    else:
                        chat_response = "抱歉，我无法执行您的查询。"
                        sql_result = {"success": False, "error": "没有可用的工具结果"}
                else:
                    # LLM直接回复，没有使用工具
                    chat_response = response.content
                    sql_result = None
            else:
                # 普通对话：直接使用LLM
                system_prompt = """你是一个友好的AI助手。当用户问及数据库相关问题时，请引导他们使用具体的数据库查询语言。

对于数据库查询，你可以建议用户：
- "查看所有数据库"
- "显示数据库xxx中的表"
- "查看表yyy的结构"
- "统计表yyy的记录数"
- "查询表yyy的数据"

请用简洁、友好的方式回答用户的问题。"""

                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=message)
                ]

                response = await self.llm.ainvoke(messages)
                chat_response = response.content
                sql_result = None

            # 添加助手回复到历史记录
            self.conversation_history.append(ChatMessage(role="assistant", content=chat_response))

            processing_time = asyncio.get_event_loop().time() - start_time

            return {
                "success": True,
                "response": chat_response,
                "sql_result": sql_result,
                "processing_time": processing_time,
                "message_type": "database_query" if self._is_database_query(message) else "general_chat"
            }

        except Exception as e:
            logger.error(f"聊天处理失败: {e}")
            processing_time = asyncio.get_event_loop().time() - start_time

            return {
                "success": False,
                "response": f"处理失败: {str(e)}",
                "sql_result": None,
                "processing_time": processing_time,
                "error_message": str(e)
            }

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []

# 全局实例
simple_database_chat = SimpleDatabaseChat()