# 智能运维助手

一个基于LangGraph的智能运维助手，采用React机制实现智能意图路由和按需系统检查，大幅提升响应速度和用户体验。

## 🚀 核心特性

### React智能路由机制
- **智能意图识别**: 自动判断用户查询类型（对话、系统信息、故障排查等）
- **按需系统检查**: 只有明确要求时才执行完整系统巡检，避免不必要的等待
- **多工作流支持**: 根据不同意图选择最优处理流程
- **性能优化**: 系统信息查询响应时间从20秒优化到0.02秒

### 工作流类型
1. **对话工作流 (chat)**: 直接LLM对话，快速响应
2. **系统信息工作流 (system_info)**: 收集基础指标，提供系统状态信息
3. **系统检查工作流 (system_check)**: 完整系统巡检和深度分析
4. **故障排查工作流 (troubleshoot)**: 智能问题分析和解决方案
5. **性能分析工作流 (performance)**: 系统性能评估和优化建议
6. **命令执行工作流 (command_exec)**: 安全的系统操作执行

### 全方位日志系统
- **结构化日志**: 使用 rotating file handlers 管理日志文件
- **LangGraph过程追踪**: 完整记录工作流执行过程
- **性能监控**: 自动记录各环节执行时间
- **错误追踪**: 详细的错误信息和堆栈跟踪

## 📁 项目结构

数据库的没写,你们自己看吧

```
yunwei/
├── conversation_router.py     # 对话路由器 - 智能意图识别和路由
├── react_ops_graph.py        # React运维助手核心工作流
├── react_chat_api.py         # React聊天API接口
├── web_app.py                # Web应用程序
├── langgraph_logger.py       # LangGraph专用日志记录器
├── logger_config.py          # 日志配置和工具
├── analyzer.py               # 系统分析器
├── monitoring.py             # 监控数据采集
├── states.py                 # 状态管理
├── config.py                 # 配置管理
├── remote_executor.py        # 远程命令执行器
├── main.py                   # 应用程序入口
└── requirements.txt          # 依赖包列表
```

## 🔄 工作流执行流程

### 1. 对话路由流程 (conversation_router.py)

```python
用户输入 → 意图分析 → 工作流选择 → 执行相应流程
```

**意图识别优先级:**
1. **强制检查关键词** (检查系统、巡检、体检等) → system_check
2. **聊天关键词** (你好、谢谢、帮助等) → chat
3. **系统信息模式** (CPU使用率、内存状态等) → system_info
4. **故障排查模式** (故障、问题、错误等) → troubleshoot
5. **性能优化模式** (优化、慢、卡顿等) → performance
6. **默认处理** → chat

### 2. React工作流主流程 (react_ops_graph.py)

```
用户查询
    ↓
意图路由分析
    ↓
工作流类型判断
    ↓
┌─────────────────────────────────────────────┐
│           选择对应工作流                    │
├─────────────────────────────────────────────┤
│ chat │ system_info │ system_check │ trouble │
│      │              │              │ shoot   │
│      │              │              │         │
│      │              │              │         │
└─────────────────────────────────────────────┘
    ↓
执行相应工作流
    ↓
生成响应
    ↓
结束对话
```

### 3. 详细工作流说明

#### 3.1 对话工作流 (chat_workflow)
**适用场景**: 问候、感谢、帮助、一般对话
**执行流程**: `route_intent → chat_response → end_conversation`
**特点**:
- 无需系统检查
- 直接调用LLM生成回复
- 响应时间: 1-3秒

```
用户: "你好"
    ↓
路由: chat (置信度: 0.98)
    ↓
直接LLM对话 → 生成回复
    ↓
响应: "你好！很高兴为您..."
```

#### 3.2 系统信息工作流 (system_info_workflow)
**适用场景**: "CPU使用率是多少"、"内存状态如何"等
**执行流程**: `route_intent → collect_basic_metrics → provide_system_info → end_conversation`
**特点**:
- 收集基础系统指标
- 可使用缓存数据（5分钟内）
- 响应时间: 0.02-0.1秒
- 包含具体数值和状态信息

```
用户: "CPU使用率是多少"
    ↓
路由: system_info (置信度: 1.00)
    ↓
收集基础指标 (可使用缓存)
    ↓
生成系统信息报告
    ↓
响应: 包含CPU使用率的详细报告
```

#### 3.3 系统检查工作流 (system_check_workflow)
**适用场景**: "检查系统"、"全面巡检"等
**执行流程**: `route_intent → collect_metrics → analyze_system → report_results → end_conversation`
**特点**:
- 完整系统指标收集
- 深度LLM分析
- 生成详细维护报告
- 响应时间: 15-25秒

```
用户: "检查系统状态"
    ↓
路由: system_check (置信度: 0.95)
    ↓
收集完整系统指标
    ↓
深度AI分析
    ↓
生成维护报告
    ↓
响应: 全面的系统健康报告
```

#### 3.4 故障排查工作流 (troubleshoot_workflow)
**适用场景**: "系统故障"、"性能问题"等
**执行流程**: `route_intent → collect_relevant_metrics → analyze_problem → provide_solution → end_conversation`
**特点**:
- 针对性指标收集
- 问题根因分析
- 具体解决步骤
- 预防措施建议

```
用户: "系统很卡怎么办"
    ↓
路由: troubleshoot (置信度: 1.00)
    ↓
收集相关指标
    ↓
问题分析
    ↓
提供解决方案
    ↓
响应: 详细的问题分析和解决步骤
```

#### 3.5 性能分析工作流 (performance_analysis_workflow)
**适用场景**: "优化系统"、"性能瓶颈"等
**执行流程**: 类似故障排查，重点关注性能指标
**特点**:
- 性能专项分析
- 瓶颈识别
- 优化方案

#### 3.6 命令执行工作流 (command_exec_workflow)
**适用场景**: "启动服务"、"重启系统"等
**执行流程**: `route_intent → validate_command → execute_command → report_results → end_conversation`
**特点**:
- 安全命令验证
- 远程执行支持
- 执行结果反馈

## 🛠 安装和使用

### 环境要求
- Python 3.8+
- 支持的操作系统: Linux, Windows, macOS

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd yunwei
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境**
```bash
# 复制并编辑配置文件
cp .env.example .env
# 编辑 .env 文件，配置必要的API密钥和参数
```

4. **启动服务**

**Web界面模式**:
```bash
python web_app.py
```

**命令行模式**:
```bash
python main.py
```

### 环境配置

**.env 文件示例**:
```env
# 通义千问API配置
DASHSCOPE_API_KEY=your_api_key_here

# Prometheus监控配置
PROMETHEUS_URL=http://localhost:9090/metrics

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=logs

# LangGraph配置
LANGGRAPH_TRACING=true
```

## 📊 API接口

### React聊天接口
```http
POST /api/chat
Content-Type: application/json

{
    "message": "CPU使用率是多少"
}
```

**响应示例**:
```json
{
    "success": true,
    "response": "系统信息报告内容...",
    "workflow_type": "system_info",
    "processing_time": 0.02,
    "session_id": "xxx-xxx-xxx",
    "system_performed_check": false
}
```

### 系统检查接口
```http
POST /api/system/check
```

### 指标获取接口
```http
GET /api/metrics
```

## 📈 性能对比

| 查询类型 | React机制前 | React机制后 | 性能提升 |
|---------|------------|------------|---------|
| 简单对话 ("你好") | 20秒 | 1.9秒 | **10.5倍** |
| 系统信息查询 | 20秒 | 0.02秒 | **1000倍** |
| 系统检查 | 20秒 | 15.7秒 | **1.3倍** |

## 📝 日志系统

### 日志文件结构
```
logs/
├── yunwei_app.log          # 应用程序主日志
├── system.log              # 系统操作日志
├── performance.log         # 性能监控日志
├── error.log               # 错误日志
├── langgraph_conversations.json  # LangGraph对话记录
└── archived/               # 归档日志目录
```

### 日志特性
- **自动轮转**: 日志文件大小限制，自动归档
- **结构化记录**: JSON格式便于分析
- **性能追踪**: 自动记录函数执行时间
- **LangGraph追踪**: 完整的工作流执行记录

## 🔧 开发指南

### 添加新的意图类型
1. 在 `conversation_router.py` 中添加新的 `IntentType`
2. 定义对应的模式匹配规则
3. 在 `react_ops_graph.py` 中创建新的工作流
4. 更新路由逻辑

### 自定义日志记录
```python
from logger_config import log_performance, log_error

@log_performance("custom_function")
def my_function():
    # 函数实现
    pass
```

### LangGraph节点日志装饰器
```python
from langgraph_logger import log_langgraph_node

@log_langgraph_node("my_node")
async def my_node_function(state):
    # 节点实现
    return state
```

## 🎯 使用示例

### 不同查询类型的响应

```bash
# 1. 简单对话 - 快速响应
用户: "你好"
工作流: chat
响应时间: ~2秒
系统检查: 否

# 2. 系统信息查询 - 极速响应
用户: "CPU使用率是多少"
工作流: system_info
响应时间: ~0.02秒
系统检查: 基础指标收集

# 3. 完整系统检查 - 深度分析
用户: "检查系统状态"
工作流: system_check
响应时间: ~15秒
系统检查: 完整巡检 + AI分析

# 4. 故障排查 - 智能分析
用户: "系统很卡怎么办"
工作流: troubleshoot
响应时间: ~10秒
系统检查: 问题分析 + 解决方案
```

---

**智能运维助手 - 让运维更智能，让响应更快速！** 🚀