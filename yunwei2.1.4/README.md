# 智能运维助手 (Intelligent Operations Assistant)

一个基于AI的智能运维监控系统，集成了实时监控、故障诊断、自动修复和知识库管理功能。

## 🚀 功能特性

### 核心功能
- **实时系统监控**：基于Prometheus的CPU、内存、磁盘、网络监控
- **AI智能分析**：使用通义千问大模型进行系统状态分析和故障诊断
- **自动修复方案**：智能生成可执行的修复计划，支持人工审核和一键执行
- **知识库管理**：基于ChromaDB的向量数据库，支持文档上传和智能检索
- **数据库管理**：支持MySQL数据库的连接、查询和管理
- **实时通信**：基于WebSocket的实时数据推送

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

### 技术架构
- **后端框架**：FastAPI + Python 3.11
- **AI集成**：LangChain + 通义千问API
- **向量数据库**：ChromaDB
- **监控系统**：Prometheus + Node Exporter
- **前端界面**：HTML5 + JavaScript + WebSocket
- **数据库**：MySQL
- **日志系统**：Python logging + 文件轮转

## 📋 系统要求

- Python 3.11+
- MySQL 8.0+
- Prometheus Server
- Node Exporter
- 通义千问API Key

## 🛠️ 安装部署

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd yunwei

# 安装Python依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件，填入必要的配置信息
```

### 2. 环境变量配置

编辑`.env`文件：

```env
# AI模型配置
DASHSCOPE_API_KEY=your_dashscope_api_key
LLM_MODEL=qwen-max

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password

# 监控配置
PROMETHEUS_URL=http://10.0.0.81:9100/metrics

# 系统配置
LOG_LEVEL=INFO
```

### 3. 启动服务

```bash
# 启动Web应用
python web_app.py

# 或使用uvicorn
uvicorn web_app:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问系统

打开浏览器访问：`http://localhost:8000`

## 📁 项目结构

```
yunwei/
├── web_app.py              # 主Web应用 (FastAPI服务器)
├── config.py               # 配置管理
├── states.py                # 数据模型定义
├── analyzer.py              # AI分析器
├── react_ops_graph.py       # LangGraph工作流引擎
├── conversation_router.py   # 智能对话路由器
├── vector_database.py       # 向量数据库管理 (ChromaDB)
├── rag_engine.py            # RAG检索引擎
├── monitoring.py            # 监控数据采集
├── database_manager.py      # 数据库管理
├── remote_executor.py       # 远程命令执行
├── logger_config.py         # 日志配置
├── langgraph_logger.py      # LangGraph日志追踪
├── fixed_embeddings.py      # 嵌入模型修复
├── main.py                  # 命令行入口
├── requirements.txt         # Python依赖
├── .env                     # 环境变量
├── static/                  # 静态文件 (CSS/JS)
├── templates/               # HTML模板
├── documents/               # 知识库文档
├── logs/                    # 日志文件
└── knowledge_base/          # 向量数据库存储
```

## 💡 使用指南

### 1. 系统监控
- 访问主页即可查看实时的系统监控数据
- 系统会自动采集CPU、内存、磁盘、网络等指标
- 当指标超过阈值时会自动产生告警

### 2. AI诊断
- 点击"执行系统检查"按钮，AI会分析当前系统状态
- 系统会生成详细的健康报告和修复建议
- 支持历史记录查看和趋势分析

### 3. 修复方案
- AI分析后会自动生成修复计划
- 可以查看详细的修复步骤、风险评估和执行命令
- 支持"一键执行"和"手动执行"两种模式
- 每个修复方案都包含回滚计划

### 4. 知识库管理
- 支持上传文档（TXT、MD、CSV、PDF等格式）
- 自动进行文档切分和向量化处理
- 支持智能问答和文档检索
- 可以重置和重新初始化知识库

### 5. 数据库管理
- 支持连接多个MySQL数据库
- 提供SQL查询界面
- 支持数据库元数据查看

## ⚙️ 配置说明

### 告警阈值配置
在`config.py`中可以修改告警阈值：

```python
THRESHOLDS = {
    'cpu_usage': 80.0,        # CPU使用率阈值(%)
    'memory_usage': 85.0,     # 内存使用率阈值(%)
    'disk_usage': 90.0,       # 磁盘使用率阈值(%)
    'load_5m': 2.0,          # 5分钟负载阈值
    'tcp_connections': 1000,  # TCP连接数阈值
}
```

### 日志配置
- 日志文件存储在`logs/`目录
- 支持自动轮转，单个文件最大10MB
- 支持不同级别的日志输出

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

## 📊 API接口

### 主要API端点

#### 系统监控
```http
GET /api/status          # 获取系统状态
GET /api/metrics         # 获取监控指标
GET /api/alerts          # 获取告警信息
```

#### AI分析
```http
POST /api/check           # 执行系统检查
POST /api/chat            # AI对话接口
POST /api/analyze-execution # 分析执行结果
```

#### 修复方案
```http
GET /api/fix-plans       # 获取修复方案
POST /api/fix-plans/approve # 审批修复方案
POST /api/execute-fix     # 执行修复方案
```

#### 知识库管理
```http
GET /api/knowledge-base/stats    # 获取知识库统计
POST /api/knowledge-base/reset    # 重置知识库
POST /api/knowledge-base/initialize # 初始化知识库
POST /api/knowledge-base/search     # 搜索知识库
POST /api/knowledge-base/chat       # 知识库对话
```

#### 数据库管理
```http
GET /api/database/databases  # 获取数据库列表
GET /api/database/tables     # 获取表列表
POST /api/database/chat      # 数据库对话
POST /api/database/execute   # 执行SQL查询
```

### WebSocket实时通信
```javascript
// 连接WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

// 接收实时数据
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    // 处理实时监控数据
};
```

## 🔧 开发指南

### 添加新的监控指标
1. 在`monitoring.py`中添加数据采集逻辑
2. 在`states.py`中定义新的数据模型
3. 在前端添加相应的显示组件

### 扩展AI分析功能
1. 修改`analyzer.py`中的系统提示词
2. 在`react_ops_graph.py`中添加新的处理节点
3. 更新修复模板和命令库

### 集成新的数据源
1. 实现新的数据采集器
2. 添加相应的配置项
3. 更新前端显示界面

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

## 🐛 故障排除

### 常见问题

1. **AI模型无法访问**
   - 检查DASHSCOPE_API_KEY是否正确配置
   - 确认网络连接正常
   - 查看日志文件中的错误信息

2. **监控数据无法获取**
   - 检查Prometheus服务是否正常运行
   - 确认Node Exporter已安装并启动
   - 验证网络连接和端口配置

3. **向量数据库初始化失败**
   - 检查`knowledge_base/`目录权限
   - 确认ChromaDB依赖已正确安装
   - 尝试重置知识库

4. **远程命令执行失败**
   - 检查SSH连接配置
   - 确认目标主机网络可达
   - 验证用户权限和密钥配置

5. **修复方案无法生成**
   - 检查AI模型配置
   - 确认监控数据正常采集
   - 查看分析器日志

### 日志查看
```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log

# 查看调试日志
tail -f logs/debug.log
```

### 性能优化建议

1. **减少AI调用频率**
   - 使用缓存机制
   - 批量处理请求
   - 设置合理的超时时间

2. **优化数据库查询**
   - 添加索引
   - 使用连接池
   - 定期清理历史数据

3. **监控资源使用**
   - 监控内存使用情况
   - 设置合理的日志轮转策略
   - 定期重启服务

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

## 📈 性能指标

| 功能模块 | 响应时间 | 可用性 | 说明 |
|---------|---------|--------|------|
| 系统监控 | <1秒 | 99.9% | 实时数据采集 |
| AI对话 | 2-5秒 | 99% | 依赖网络和API |
| 系统检查 | 15-25秒 | 98% | 完整分析流程 |
| 修复执行 | 10-30秒 | 95% | 依赖目标系统 |
| 知识库检索 | 1-3秒 | 99.5% | 向量搜索 |

## 🤝 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交Issue：[GitHub Issues](https://github.com/your-repo/issues)
- 邮件联系：your-email@example.com

## 🙏 致谢

感谢以下开源项目的支持：
- [FastAPI](https://fastapi.tiangolo.com/)
- [LangChain](https://python.langchain.com/)
- [ChromaDB](https://www.trychroma.com/)
- [Prometheus](https://prometheus.io/)
- [通义千问](https://qianwen.aliyun.com/)

---

**智能运维助手 - 让运维更智能，让系统更稳定！** 🚀