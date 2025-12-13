// 智能运维助手前端JavaScript

// 全局变量
let websocket = null;
let cpuChart = null;
let memoryChart = null;
let autoRefreshInterval = null;
let currentSection = 'dashboard';
let chatMessages = [];
let chatMessageCount = 0;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// 初始化应用
function initializeApp() {
    initializeWebSocket();
    initializeCharts();
    initializeNavigation();
    loadInitialData();
    startAutoRefresh();
    showNotification('success', '系统启动', '智能运维助手已成功启动');
}

// WebSocket连接
function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    websocket = new WebSocket(wsUrl);

    websocket.onopen = function(event) {
        console.log('WebSocket连接已建立');
        updateConnectionStatus(true);
    };

    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    websocket.onclose = function(event) {
        console.log('WebSocket连接已关闭');
        updateConnectionStatus(false);
        // 尝试重连
        setTimeout(initializeWebSocket, 5000);
    };

    websocket.onerror = function(error) {
        console.error('WebSocket错误:', error);
        updateConnectionStatus(false);
    };
}

// 处理WebSocket消息
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'check_started':
            updateCheckStatus('正在收集监控数据和分析系统状态...');
            break;
        case 'check_completed':
            updateCheckStatus('系统检查完成！');
            closeModal('checkModal');
            showNotification('success', '检查完成', '系统检查已成功完成');

            // 显示AI建议和修复方案
            if (data.data && data.data.context && data.data.context.analysis_result) {
                displayAISuggestions(data.data.context.analysis_result);
            }

            // 显示修复方案 - 从多个可能的数据源获取
            let fixPlans = [];
            if (data.fix_plans && data.fix_plans.length > 0) {
                fixPlans = data.fix_plans;
            } else if (data.data && data.data.fix_plans && data.data.fix_plans.length > 0) {
                fixPlans = data.data.fix_plans;
            } else if (data.state && data.state.fix_plans && data.state.fix_plans.length > 0) {
                fixPlans = data.state.fix_plans;
            } else if (data.data && data.data.state && data.data.state.fix_plans && data.data.state.fix_plans.length > 0) {
                fixPlans = data.data.state.fix_plans;
            }

            if (fixPlans.length > 0) {
                console.log('显示修复方案:', fixPlans);
                window.currentFixPlans = fixPlans;
                displayFixPlans(fixPlans);
            }

            refreshData();
            break;
        case 'check_failed':
            updateCheckStatus('检查失败');
            closeModal('checkModal');
            showNotification('error', '检查失败', data.message);
            break;
        case 'check_error':
            updateCheckStatus('检查过程中发生错误');
            closeModal('checkModal');
            showNotification('error', '检查错误', data.message);
            break;
        case 'pong':
            // 心跳响应
            break;
        case 'execution_started':
            showNotification('info', '执行开始', data.message);
            break;
        case 'execution_completed':
            showNotification('success', '执行完成', data.message);
            if (data.success) {
                document.getElementById('executionStatus').textContent = '执行成功';
            } else {
                document.getElementById('executionStatus').textContent = '部分失败';
            }
            break;
        case 'execution_failed':
            showNotification('error', '执行失败', data.message);
            document.getElementById('executionStatus').textContent = '执行失败';
            break;
        default:
            console.log('未知消息类型:', data.type);
    }
}

// 更新连接状态
function updateConnectionStatus(connected) {
    const statusIcon = document.getElementById('connectionStatus');
    const statusText = document.getElementById('statusText');

    if (connected) {
        statusIcon.className = 'fas fa-circle text-success';
        statusText.textContent = '已连接';
    } else {
        statusIcon.className = 'fas fa-circle text-danger';
        statusText.textContent = '连接断开';
    }
}

// 初始化图表
function initializeCharts() {
    // CPU使用率图表
    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
    cpuChart = new Chart(cpuCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'CPU使用率 (%)',
                data: [],
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });

    // 内存使用率图表
    const memoryCtx = document.getElementById('memoryChart').getContext('2d');
    memoryChart = new Chart(memoryCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '内存使用率 (%)',
                data: [],
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// 初始化导航
function initializeNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            showSection(targetId);

            // 更新活动状态
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// 显示指定页面
function showSection(sectionId) {
    // 隐藏所有页面
    const sections = ['dashboard', 'metrics', 'alerts', 'history', 'ai-chat', 'database', 'config'];
    sections.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.style.display = id === sectionId ? 'block' : 'none';
        }
    });

    currentSection = sectionId;

    // 根据页面加载相应数据
    switch (sectionId) {
        case 'metrics':
            loadMetricsData();
            break;
        case 'alerts':
            loadAlertsData();
            break;
        case 'history':
            loadHistoryData();
            break;
        case 'database':
            loadDatabases();
            break;
        case 'config':
            loadConfigData();
            break;
        case 'ai-chat':
            // 初始化对话界面
            initializeChatInterface();
            break;
    }
}

// 加载初始数据
async function loadInitialData() {
    try {
        await Promise.all([
            loadStatusData(),
            loadChartsData()
        ]);
    } catch (error) {
        console.error('加载初始数据失败:', error);
        showNotification('error', '数据加载失败', error.message);
    }
}

// 加载状态数据
async function loadStatusData() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // 更新状态卡片
        document.getElementById('systemStatus').textContent = data.status;
        document.getElementById('metricsCount').textContent = data.metrics_count;
        document.getElementById('alertsCount').textContent = data.alerts_count;

        // 更新最后检查时间
        if (data.data.last_check) {
            const checkTime = new Date(data.data.last_check).toLocaleString('zh-CN');
            document.getElementById('lastCheck').textContent = checkTime;
        }

    } catch (error) {
        console.error('加载状态数据失败:', error);
    }
}

// 加载图表数据
async function loadChartsData() {
    try {
        const response = await fetch('/api/metrics');
        const data = await response.json();

        // 更新CPU图表
        const cpuMetric = data.cpu_metrics.find(m => m.name === 'cpu_usage_percent');
        if (cpuMetric) {
            updateChart(cpuChart, cpuMetric.value);
        }

        // 更新内存图表
        const memoryMetric = data.memory_metrics.find(m => m.name === 'memory_usage_percent');
        if (memoryMetric) {
            updateChart(memoryChart, memoryMetric.value);
        }

    } catch (error) {
        console.error('加载图表数据失败:', error);
    }
}

// 更新图表
function updateChart(chart, value) {
    const now = new Date().toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });

    // 添加新数据点
    chart.data.labels.push(now);
    chart.data.datasets[0].data.push(value);

    // 限制显示的数据点数量
    if (chart.data.labels.length > 20) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
    }

    chart.update('none');
}

// 加载监控指标详情
async function loadMetricsData() {
    try {
        const response = await fetch('/api/metrics');
        const data = await response.json();

        displayMetricsList('cpuMetricsList', data.cpu_metrics);
        displayMetricsList('memoryMetricsList', data.memory_metrics);
        displayMetricsList('diskMetricsList', data.disk_metrics);
        displayMetricsList('networkMetricsList', data.network_metrics);

    } catch (error) {
        console.error('加载监控指标失败:', error);
        showNotification('error', '数据加载失败', error.message);
    }
}

// 显示指标列表
function displayMetricsList(containerId, metrics) {
    const container = document.getElementById(containerId);
    if (!container || !metrics || metrics.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无数据</p>';
        return;
    }

    const html = metrics.map(metric => {
        const status = metric.status === 'critical' ? 'danger' :
                      metric.status === 'warning' ? 'warning' : '';
        const statusClass = status ? ` ${status}` : '';
        const valueClass = status ? ` ${status}` : '';
        const threshold = metric.threshold ? `<div class="metric-threshold">阈值: ${metric.threshold}${metric.unit}</div>` : '';

        return `
            <div class="metric-item${statusClass}">
                <div>
                    <div class="metric-name">${metric.name}</div>
                    ${threshold}
                </div>
                <div class="metric-value${valueClass}">${metric.value.toFixed(2)}${metric.unit}</div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

// 加载告警数据
async function loadAlertsData() {
    try {
        const response = await fetch('/api/alerts');
        const data = await response.json();

        // 更新徽章
        document.getElementById('criticalAlertsBadge').textContent = `${data.critical_count} 严重`;
        document.getElementById('warningAlertsBadge').textContent = `${data.warning_count} 警告`;

        // 显示告警列表
        displayAlertsList(data.alerts);

    } catch (error) {
        console.error('加载告警数据失败:', error);
        showNotification('error', '数据加载失败', error.message);
    }
}

// 显示告警列表
function displayAlertsList(alerts) {
    const container = document.getElementById('alertsList');
    if (!container) return;

    if (!alerts || alerts.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无活跃告警</p>';
        return;
    }

    const html = alerts.map(alert => {
        const levelClass = alert.level;
        const alertTime = new Date(alert.timestamp).toLocaleString('zh-CN');

        let suggestionsHtml = '';
        if (alert.suggested_actions && alert.suggested_actions.length > 0) {
            suggestionsHtml = `
                <div class="alert-suggestions">
                    <strong>建议操作:</strong>
                    <ul>
                        ${alert.suggested_actions.map(action => `<li>${action}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        return `
            <div class="alert-item ${levelClass}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <span class="alert-level ${levelClass}">${alert.level}</span>
                        <h6 class="alert-message">${alert.message}</h6>
                        <div class="alert-details">
                            <strong>指标:</strong> ${alert.metric_name}<br>
                            <strong>当前值:</strong> ${alert.value}<br>
                            <strong>阈值:</strong> ${alert.threshold}<br>
                            <strong>时间:</strong> ${alertTime}
                        </div>
                        ${suggestionsHtml}
                    </div>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

// 加载历史数据
async function loadHistoryData() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();

        displayActionHistory(data.action_history);
        displayConversationHistory(data.conversation_history);

    } catch (error) {
        console.error('加载历史数据失败:', error);
        showNotification('error', '数据加载失败', error.message);
    }
}

// 显示操作历史
function displayActionHistory(history) {
    const container = document.getElementById('actionHistory');
    if (!container) return;

    if (!history || history.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无操作记录</p>';
        return;
    }

    const html = history.slice(-10).reverse().map(item => {
        const time = new Date(item.timestamp).toLocaleString('zh-CN');
        return `
            <div class="history-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="history-type">${item.type}</div>
                        <div class="history-details">
                            ${JSON.stringify(item.details, null, 2)}
                        </div>
                    </div>
                    <div class="history-timestamp">${time}</div>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

// 显示对话历史
function displayConversationHistory(history) {
    const container = document.getElementById('conversationHistory');
    if (!container) return;

    if (!history || history.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无对话记录</p>';
        return;
    }

    const html = history.slice(-10).reverse().map(item => {
        const time = new Date(item.timestamp).toLocaleString('zh-CN');
        return `
            <div class="history-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="history-type">用户查询</div>
                        <div class="history-details">${item.user}</div>
                    </div>
                    <div class="history-timestamp">${time}</div>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

// 加载配置数据
async function loadConfigData() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();

        displayServerConfig(data);
        displayThresholdConfig(data.thresholds);

    } catch (error) {
        console.error('加载配置数据失败:', error);
        showNotification('error', '数据加载失败', error.message);
    }
}

// 显示服务器配置
function displayServerConfig(config) {
    const container = document.getElementById('serverConfig');
    if (!container) return;

    const html = `
        <div class="config-item">
            <span class="config-label">目标服务器</span>
            <span class="config-value">${config.server_host}</span>
        </div>
        <div class="config-item">
            <span class="config-label">Prometheus地址</span>
            <span class="config-value">${config.prometheus_url}</span>
        </div>
        <div class="config-item">
            <span class="config-label">AI模型</span>
            <span class="config-value">${config.llm_model}</span>
        </div>
    `;

    container.innerHTML = html;
}

// 显示阈值配置
function displayThresholdConfig(thresholds) {
    const container = document.getElementById('thresholdConfig');
    if (!container) return;

    const html = `
        <div class="threshold-item">
            <span class="threshold-name">CPU使用率阈值</span>
            <span class="threshold-value">${thresholds.cpu_usage}%</span>
        </div>
        <div class="threshold-item">
            <span class="threshold-name">内存使用率阈值</span>
            <span class="threshold-value">${thresholds.memory_usage}%</span>
        </div>
        <div class="threshold-item">
            <span class="threshold-name">磁盘使用率阈值</span>
            <span class="threshold-value">${thresholds.disk_usage}%</span>
        </div>
        <div class="threshold-item">
            <span class="threshold-name">系统负载阈值</span>
            <span class="threshold-value">${thresholds.load_average}</span>
        </div>
        <div class="threshold-item">
            <span class="threshold-name">连接数阈值</span>
            <span class="threshold-value">${thresholds.connection_count}</span>
        </div>
    `;

    container.innerHTML = html;
}

// 执行系统检查
async function runSystemCheck() {
    const modal = new bootstrap.Modal(document.getElementById('checkModal'));
    modal.show();

    try {
        const response = await fetch('/api/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ auto_fix: false })
        });

        const result = await response.json();

        if (!result.success) {
            closeModal('checkModal');
            showNotification('error', '检查失败', result.error || '未知错误');
        }

    } catch (error) {
        closeModal('checkModal');
        showNotification('error', '请求失败', error.message);
    }
}

// 更新检查状态
function updateCheckStatus(message) {
    const statusElement = document.getElementById('checkStatus');
    if (statusElement) {
        statusElement.textContent = message;
    }
}

// 刷新数据
function refreshData() {
    loadStatusData();
    loadChartsData();

    if (currentSection === 'metrics') {
        loadMetricsData();
    } else if (currentSection === 'alerts') {
        loadAlertsData();
    } else if (currentSection === 'history') {
        loadHistoryData();
    } else if (currentSection === 'config') {
        loadConfigData();
    }
}

// 自动刷新
function startAutoRefresh() {
    // 每30秒自动刷新一次
    autoRefreshInterval = setInterval(() => {
        if (document.visibilityState === 'visible') {
            refreshData();
        }
    }, 30000);
}

// 停止自动刷新
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// 显示通知
function showNotification(type, title, message) {
    const container = document.getElementById('notificationContainer');

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <button class="notification-close" onclick="this.parentElement.remove()">&times;</button>
        <div class="notification-title">${title}</div>
        <div class="notification-message">${message}</div>
    `;

    container.appendChild(notification);

    // 自动移除通知
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// 关闭模态框
function closeModal(modalId) {
    const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
    if (modal) {
        modal.hide();
    }
}

// 页面可见性变化时的处理
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
        // 页面变为可见时刷新数据
        refreshData();
    }
});

// WebSocket心跳
setInterval(() => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ type: 'ping' }));
    }
}, 30000);

// ===== 智能对话功能 =====

// 发送消息
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message) return;

    // 添加用户消息到界面
    addChatMessage('user', message);
    input.value = '';

    // 显示AI正在思考
    showTypingIndicator();

    try {
        // 调用AI对话API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });

        const result = await response.json();

        // 隐藏思考指示器
        hideTypingIndicator();

        if (result.success) {
            // 添加AI回复
            addChatMessage('ai', result.response);

            // 更新统计
            updateChatStats();
        } else {
            addChatMessage('ai', '抱歉，我现在无法回答这个问题。请稍后再试。');
        }

    } catch (error) {
        hideTypingIndicator();
        addChatMessage('ai', '网络连接出现问题，请检查网络连接后重试。');
        console.error('对话请求失败:', error);
    }
}

// 添加聊天消息到界面
function addChatMessage(type, message) {
    const chatContainer = document.getElementById('chatMessages');
    const messageTime = new Date().toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
    });

    // 如果是第一条消息，清除欢迎语
    if (chatMessages.length === 0) {
        chatContainer.innerHTML = '';
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;

    messageDiv.innerHTML = `
        <div class="d-flex ${type === 'user' ? 'justify-content-end' : 'justify-content-start'} align-items-end mb-3">
            ${type === 'ai' ? '<div class="chat-avatar ai"><i class="fas fa-robot"></i></div>' : ''}
            <div>
                <div class="chat-bubble">
                    ${formatMessage(message)}
                </div>
                <div class="chat-time">${messageTime}</div>
            </div>
            ${type === 'user' ? '<div class="chat-avatar user"><i class="fas fa-user"></i></div>' : ''}
        </div>
    `;

    chatContainer.appendChild(messageDiv);

    // 滚动到底部
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // 保存到消息列表
    chatMessages.push({
        type: type,
        message: message,
        time: new Date().toISOString()
    });

    chatMessageCount++;
}

// 格式化消息内容
function formatMessage(message) {
    // 处理换行
    message = message.replace(/\n/g, '<br>');

    // 处理代码块
    message = message.replace(/```([^`]+)```/g, '<pre class="mt-2 mb-2 p-2 bg-light rounded"><code>$1</code></pre>');

    // 处理行内代码
    message = message.replace(/`([^`]+)`/g, '<code class="bg-light px-1 rounded">$1</code>');

    // 处理加粗
    message = message.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    return message;
}

// 显示AI思考指示器
function showTypingIndicator() {
    const chatContainer = document.getElementById('chatMessages');

    // 如果是第一条消息，清除欢迎语
    if (chatMessages.length === 0) {
        chatContainer.innerHTML = '';
    }

    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-message ai typing-indicator show';
    typingDiv.id = 'typingIndicator';

    typingDiv.innerHTML = `
        <div class="d-flex justify-content-start align-items-end mb-3">
            <div class="chat-avatar ai"><i class="fas fa-robot"></i></div>
            <div>
                <div class="chat-bubble">
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        </div>
    `;

    chatContainer.appendChild(typingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// 隐藏AI思考指示器
function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// 快捷问题
function quickQuestion(type) {
    const questions = {
        'status': '请分析当前系统状态',
        'check': '如何执行系统检查？',
        'cpu': 'CPU使用率情况如何？',
        'memory': '内存使用情况怎么样？',
        'disk': '磁盘空间使用情况如何？',
        'alerts': '当前有哪些系统告警？',
        'optimize': '请提供系统性能优化建议',
        'load': '系统负载过高，请分析原因并提供解决方案',
        'memory-optimize': '如何优化内存使用？',
        'disk-cleanup': '磁盘空间满了，请提供清理建议',
        'security': '请进行系统安全检查'
    };

    const question = questions[type] || type;
    document.getElementById('chatInput').value = question;
    sendMessage();
}

// 清空对话
function clearChat() {
    const chatContainer = document.getElementById('chatMessages');
    chatContainer.innerHTML = `
        <div class="text-center text-muted">
            <i class="fas fa-robot fa-2x mb-3"></i>
            <p>开始与智能运维助手对话吧！</p>
            <small>你可以询问系统状态、监控数据、故障诊断等问题</small>
        </div>
    `;
    chatMessages = [];
    chatMessageCount = 0;
    updateChatStats();
}

// 更新对话统计
function updateChatStats() {
    // 计算今日对话数量（简化处理，实际应该从服务器获取）
    const today = new Date().toDateString();
    const todayMessages = chatMessages.filter(msg =>
        new Date(msg.time).toDateString() === today
    ).length / 2; // 除以2因为每个对话包含用户和AI两条消息

    document.getElementById('todayChats').textContent = todayMessages;
    document.getElementById('totalMessages').textContent = chatMessageCount;
}

// 显示AI建议
function displayAISuggestions(analysisResult) {
    const suggestionsSection = document.getElementById('aiSuggestionsSection');
    const suggestionsContent = document.getElementById('aiSuggestionsContent');

    if (!analysisResult || !analysisResult.detected_issues || analysisResult.detected_issues.length === 0) {
        suggestionsSection.style.display = 'none';
        return;
    }

    // 显示建议区域
    suggestionsSection.style.display = 'block';

    // 生成建议内容
    let suggestionsHtml = '';

    // 检测到的问题
    if (analysisResult.detected_issues && analysisResult.detected_issues.length > 0) {
        suggestionsHtml += `
            <div class="ai-suggestion-card">
                <div class="ai-suggestion-header">
                    <i class="fas fa-exclamation-triangle"></i>
                    <div class="ai-suggestion-title">检测到的问题</div>
                </div>
                <div class="ai-suggestion-content">
                    <ul>
                        ${analysisResult.detected_issues.map(issue => `<li>${issue}</li>`).join('')}
                    </ul>
                </div>
            </div>
        `;
    }

    // 建议操作
    if (analysisResult.recommended_actions && analysisResult.recommended_actions.length > 0) {
        suggestionsHtml += `
            <div class="ai-suggestion-card">
                <div class="ai-suggestion-header">
                    <i class="fas fa-tools"></i>
                    <div class="ai-suggestion-title">建议操作</div>
                </div>
                <div class="ai-suggestion-content">
                    ${analysisResult.recommended_actions.map(action => `<p>• ${action}</p>`).join('')}
                </div>
                <div class="ai-suggestion-actions">
                    <h6>风险评估</h6>
                    <p>${analysisResult.urgency === 'high' ? '高优先级' : analysisResult.urgency === 'medium' ? '中优先级' : '低优先级'}</p>
                </div>
            </div>
        `;
    }

    // 系统状态评估
    if (analysisResult.overall_status) {
        suggestionsHtml += `
            <div class="ai-suggestion-card">
                <div class="ai-suggestion-header">
                    <i class="fas fa-clipboard-check"></i>
                    <div class="ai-suggestion-title">系统状态评估</div>
                </div>
                <div class="ai-suggestion-content">
                    <p>总体状态: <strong>${analysisResult.overall_status}</strong></p>
                    ${analysisResult.auto_fixable ? '<p>✓ 可自动修复</p>' : '<p>⚠ 需要人工干预</p>'}
                </div>
            </div>
        `;
    }

    suggestionsContent.innerHTML = suggestionsHtml;
}

// 初始化对话界面
function initializeChatInterface() {
    // 如果有历史消息，恢复显示
    if (chatMessages.length === 0) {
        // 从服务器加载对话历史
        loadChatHistory();
    }

    // 更新对话统计
    updateChatStats();
}

// 加载对话历史
async function loadChatHistory() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();

        if (data.conversation_history && data.conversation_history.length > 0) {
            const chatContainer = document.getElementById('chatMessages');
            chatContainer.innerHTML = '';

            // 显示历史对话
            data.conversation_history.forEach(item => {
                if (item.user) {
                    addChatMessage('user', item.user);
                }
                if (item.ai) {
                    addChatMessage('ai', item.ai);
                }
            });

            // 滚动到底部
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    } catch (error) {
        console.error('加载对话历史失败:', error);
    }
}

// ===== 修复方案功能 =====

// 显示修复方案
function displayFixPlans(fixPlans) {
    const fixPlansSection = document.getElementById('fixPlansSection');
    const fixPlansContent = document.getElementById('fixPlansContent');
    const fixPlansCount = document.getElementById('fixPlansCount');

    if (!fixPlans || fixPlans.length === 0) {
        fixPlansSection.style.display = 'none';
        return;
    }

    // 显示修复方案区域
    fixPlansSection.style.display = 'block';
    fixPlansCount.textContent = `${fixPlans.length} 个方案`;

    // 生成修复方案内容
    let plansHtml = '';

    fixPlans.forEach((plan, index) => {
        const priorityClass = plan.priority === 'critical' ? 'danger' :
                              plan.priority === 'high' ? 'warning' :
                              plan.priority === 'medium' ? 'info' : 'secondary';

        const riskClass = plan.risk_level === 'critical' ? 'danger' :
                         plan.risk_level === 'high' ? 'warning' :
                         plan.risk_level === 'medium' ? 'info' : 'success';

        const planId = plan.id || `plan_${index + 1}`;
        const isFollowupPlan = planId && planId.includes('followup');
        const planTypeBadge = isFollowupPlan ?
            '<span class="badge bg-success me-2"><i class="fas fa-brain"></i> AI智能分析</span>' :
            '';

        plansHtml += `
            <div class="fix-plan-card card mb-3 ${isFollowupPlan ? 'border-success' : ''}" data-plan-id="${planId}">
                <div class="card-header d-flex justify-content-between align-items-center ${isFollowupPlan ? 'bg-success text-white' : ''}">
                    <div class="d-flex align-items-center">
                        ${planTypeBadge}
                        <span class="badge bg-${priorityClass} me-2">${plan.priority || 'medium'}</span>
                        <h6 class="mb-0">${plan.issue || '修复方案'}</h6>
                    </div>
                    <div class="d-flex align-items-center">
                        <span class="badge bg-${riskClass} me-2">风险: ${plan.risk_level || 'low'}</span>
                        <small class="text-muted">${plan.estimated_time || '未知'}分钟</small>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <div class="fix-description">
                                ${isFollowupPlan ? `
                                    <div class="alert alert-success alert-sm mb-3">
                                        <i class="fas fa-brain"></i>
                                        <strong>AI智能分析结果</strong><br>
                                        <small>此方案基于实际执行结果分析生成，使用真实的进程PID</small>
                                    </div>
                                ` : ''}
                                <h6>问题描述</h6>
                                <p class="text-muted">${plan.description || '暂无详细描述'}</p>

                                <h6 class="mt-3">前置条件</h6>
                                <ul class="text-muted small">
                                    ${(plan.preconditions && plan.preconditions.length > 0) ?
                                        plan.preconditions.map(cond => `<li>${cond}</li>`).join('') :
                                        '<li>无特殊前置条件</li>'
                                    }
                                </ul>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="fix-actions text-end">
                                <button class="btn btn-outline-primary btn-sm mb-2" onclick="viewPlanDetails('${planId}')">
                                    <i class="fas fa-eye"></i> 查看详情
                                </button>
                                <br>
                                <button class="btn btn-success btn-sm mb-2" onclick="approvePlan('${planId}')">
                                    <i class="fas fa-check"></i> 执行方案
                                </button>
                                <br>
                                <button class="btn btn-outline-secondary btn-sm" onclick="rejectPlan('${planId}')">
                                    <i class="fas fa-times"></i> 拒绝方案
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    fixPlansContent.innerHTML = plansHtml;
}

// 查看修复方案详情
function viewPlanDetails(planId) {
    console.log('查看详情:', planId);

    // 隐藏其他方案的详情
    document.querySelectorAll('.plan-details-section').forEach(section => {
        section.style.display = 'none';
    });

    // 找到对应方案
    const plan = window.currentFixPlans && window.currentFixPlans.find(p =>
        p.id === planId ||
        `plan_${window.currentFixPlans.indexOf(p) + 1}` === planId
    );

    if (!plan) {
        console.error('未找到方案:', planId);
        showNotification('error', '错误', `未找到修复方案: ${planId}`);
        return;
    }

    // 在修复方案卡片下方显示详情
    const planCard = document.querySelector(`[data-plan-id="${planId}"]`);
    if (!planCard) {
        console.error('未找到方案卡片:', planId);
        return;
    }

    // 检查是否已经有详情区域
    let detailsSection = planCard.querySelector('.plan-details-section');
    if (!detailsSection) {
        detailsSection = document.createElement('div');
        detailsSection.className = 'plan-details-section';
        detailsSection.style.marginTop = '15px';
        planCard.appendChild(detailsSection);
    }

    // 显示命令详情
    const commands = plan.commands || [];
    let commandsHtml = '<h6><i class="fas fa-code"></i> 执行命令:</h6>';

    if (commands.length > 0) {
        commandsHtml += '<div class="command-list">';
        commands.forEach((cmd, index) => {
            commandsHtml += `
                <div class="command-item mb-3 p-3 bg-light rounded" data-command-index="${index}">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <strong>步骤 ${index + 1}: <span class="command-description">${cmd.description || '执行命令'}</span></strong>
                        <div>
                            <span class="badge bg-info">超时: ${cmd.timeout || 30}秒</span>
                            <button class="btn btn-outline-primary btn-sm ms-2" onclick="toggleCommandEdit(${index})" title="编辑命令">
                                <i class="fas fa-edit"></i> 编辑
                            </button>
                        </div>
                    </div>

                    <!-- 显示模式 -->
                    <div class="command-display" id="display-${index}">
                        <div class="command-code">
                            <pre class="mb-2 p-2 bg-dark text-white rounded"><code>${cmd.command || '无命令'}</code></pre>
                        </div>
                        ${cmd.expected_output ? `<div class="text-muted small"><i class="fas fa-check-circle"></i> 预期输出: ${cmd.expected_output}</div>` : ''}
                    </div>

                    <!-- 编辑模式 -->
                    <div class="command-edit" id="edit-${index}" style="display: none;">
                        <div class="mb-2">
                            <label class="form-label">步骤描述:</label>
                            <input type="text" class="form-control form-control-sm" id="desc-${index}" value="${cmd.description || ''}" placeholder="输入步骤描述">
                        </div>
                        <div class="mb-2">
                            <label class="form-label">执行命令:</label>
                            <textarea class="form-control form-control-sm font-monospace" id="cmd-${index}" rows="3" placeholder="输入Shell命令">${cmd.command || ''}</textarea>
                        </div>
                        <div class="mb-2">
                            <label class="form-label">预期输出:</label>
                            <input type="text" class="form-control form-control-sm" id="output-${index}" value="${cmd.expected_output || ''}" placeholder="输入预期输出">
                        </div>
                        <div class="mb-2">
                            <label class="form-label">超时时间(秒):</label>
                            <input type="number" class="form-control form-control-sm" id="timeout-${index}" value="${cmd.timeout || 30}" min="1" max="300">
                        </div>
                        <div class="d-flex gap-2">
                            <button class="btn btn-success btn-sm" onclick="saveCommandEdit(${index})">
                                <i class="fas fa-save"></i> 保存
                            </button>
                            <button class="btn btn-secondary btn-sm" onclick="cancelCommandEdit(${index})">
                                <i class="fas fa-times"></i> 取消
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        commandsHtml += '</div>';
    } else {
        commandsHtml = '<div class="alert alert-warning"><i class="fas fa-exclamation-triangle"></i> 暂无可执行命令</div>';
    }

    // 添加回滚和验证信息
    const rollbackCommands = plan.rollback_commands || [];
    const verificationCommands = plan.verification_commands || [];

    let additionalInfo = '';
    if (rollbackCommands.length > 0) {
        additionalInfo += `
            <div class="mt-3">
                <h6><i class="fas fa-undo"></i> 回滚方案:</h6>
                <div class="alert alert-warning">
                    ${rollbackCommands.map((cmd, i) => `${i + 1}. ${cmd}`).join('<br>')}
                </div>
            </div>
        `;
    }

    if (verificationCommands.length > 0) {
        additionalInfo += `
            <div class="mt-3">
                <h6><i class="fas fa-check-double"></i> 验证步骤:</h6>
                <div class="alert alert-info">
                    ${verificationCommands.map((cmd, i) => `${i + 1}. ${cmd}`).join('<br>')}
                </div>
            </div>
        `;
    }

    detailsSection.innerHTML = `
        <div class="card border-primary">
            <div class="card-header bg-primary text-white">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-0"><i class="fas fa-eye"></i> 方案详情 - ${plan.issue || '修复方案'}</h6>
                    <button class="btn btn-outline-light btn-sm" onclick="hidePlanDetails('${planId}')">
                        <i class="fas fa-times"></i> 收起
                    </button>
                </div>
            </div>
            <div class="card-body">
                ${commandsHtml}
                ${additionalInfo}
            </div>
        </div>
    `;

    detailsSection.style.display = 'block';

    // 滚动到详情区域
    detailsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// 隐藏修复方案详情
function hidePlanDetails(planId) {
    const planCard = document.querySelector(`[data-plan-id="${planId}"]`);
    if (planCard) {
        const detailsSection = planCard.querySelector('.plan-details-section');
        if (detailsSection) {
            detailsSection.style.display = 'none';
        }
    }
}

// 在详情区域显示执行结果
function showExecutionResultsInDetails(planId, result) {
    const planCard = document.querySelector(`[data-plan-id="${planId}"]`);
    if (!planCard) return;

    // 查找或创建执行结果区域
    let resultsSection = planCard.querySelector('.execution-results-section');
    if (!resultsSection) {
        resultsSection = document.createElement('div');
        resultsSection.className = 'execution-results-section mt-3';
        planCard.appendChild(resultsSection);
    }

    resultsSection.innerHTML = `
        <div class="card border-success">
            <div class="card-header bg-success text-white">
                <h6 class="mb-0"><i class="fas fa-play-circle"></i> 执行结果</h6>
            </div>
            <div class="card-body">
                <div class="alert alert-info">
                    <i class="fas fa-spinner fa-spin"></i>
                    <strong>执行状态:</strong> 正在执行中...
                </div>
                <div id="execution-details-${planId}">
                    <p class="text-muted">等待执行结果...</p>
                </div>
            </div>
        </div>
    `;

    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// 更新详情区域的执行结果
function updateExecutionResultsInDetails(planId, results) {
    const detailsElement = document.getElementById(`execution-details-${planId}`);
    if (!detailsElement) return;

    let resultsHtml = '';

    if (results.commands && results.commands.length > 0) {
        resultsHtml = '<div class="execution-commands">';
        results.commands.forEach((cmd, index) => {
            const statusClass = cmd.success === true ? 'success' :
                              cmd.success === false ? 'danger' : 'info';
            const statusIcon = cmd.success === true ? 'check-circle' :
                              cmd.success === false ? 'times-circle' : 'spinner fa-spin';

            resultsHtml += `
                <div class="command-result mb-3 p-3 bg-light rounded">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <strong>步骤 ${index + 1}: ${cmd.description || '执行命令'}</strong>
                        <span class="badge bg-${statusClass}">
                            <i class="fas fa-${statusIcon}"></i>
                            ${cmd.success === true ? '成功' : cmd.success === false ? '失败' : '执行中'}
                        </span>
                    </div>
                    <div class="command-executed">
                        <pre class="mb-2 p-2 bg-dark text-white rounded small"><code>${cmd.command || '无命令'}</code></pre>
                    </div>
                    ${cmd.output ? `
                        <div class="command-output mt-2">
                            <strong>输出:</strong>
                            <pre class="bg-white border p-2 rounded small">${cmd.output}</pre>
                        </div>
                    ` : ''}
                    ${cmd.error ? `
                        <div class="command-error mt-2">
                            <strong>错误:</strong>
                            <pre class="bg-danger text-white p-2 rounded small">${cmd.error}</pre>
                        </div>
                    ` : ''}
                </div>
            `;
        });
        resultsHtml += '</div>';
    } else {
        resultsHtml = '<p class="text-muted">暂无执行结果</p>';
    }

    // 添加执行总结
    if (results.completed) {
        const successCount = results.commands ? results.commands.filter(c => c.success === true).length : 0;
        const totalCount = results.commands ? results.commands.length : 0;

        resultsHtml += `
            <div class="execution-summary mt-3">
                <div class="alert ${successCount === totalCount ? 'alert-success' : 'alert-warning'}">
                    <h6><i class="fas fa-flag-checkered"></i> 执行完成</h6>
                    <p class="mb-0">
                        成功: ${successCount}/${totalCount} 个命令
                        ${successCount === totalCount ? '✅ 所有命令执行成功' : '⚠️ 部分命令执行失败'}
                    </p>
                </div>
            </div>
        `;
    }

    detailsElement.innerHTML = resultsHtml;
}

// 创建修复方案详情模态框
function createPlanDetailsModal() {
    const modalHtml = `
        <div class="modal fade" id="planDetailsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">修复方案详情</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div id="planDetailsContent"></div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        <button type="button" class="btn btn-success" onclick="executePlanFromModal()">
                            <i class="fas fa-play"></i> 立即执行
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// 填充修复方案详情
function fillPlanDetails(planId) {
    const content = document.getElementById('planDetailsContent');

    console.log('查找方案ID:', planId, '当前修复方案:', window.currentFixPlans);

    // 改进方案查找逻辑
    let plan = null;
    if (window.currentFixPlans) {
        // 首先尝试直接匹配ID
        plan = window.currentFixPlans.find(p => p.id === planId);

        // 如果没找到，尝试索引方式
        if (!plan) {
            const index = parseInt(planId.replace('plan_', '')) - 1;
            if (index >= 0 && index < window.currentFixPlans.length) {
                plan = window.currentFixPlans[index];
            }
        }

        // 如果还是没找到，尝试所有可能的匹配方式
        if (!plan) {
            plan = window.currentFixPlans.find(p =>
                p.id === planId ||
                `plan_${window.currentFixPlans.indexOf(p) + 1}` === planId ||
                `plan_${window.currentFixPlans.indexOf(p)}` === planId
            );
        }
    }

    console.log('找到的方案:', plan);

    if (!plan) {
        content.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>未找到修复方案详情</strong>
                <br>
                <small>方案ID: ${planId}</small>
                <br>
                <small>可用方案: ${window.currentFixPlans ? window.currentFixPlans.length : 0} 个</small>
            </div>
        `;
        return;
    }

    window.selectedPlanId = planId;

    let detailsHtml = `
        <div class="plan-overview">
            <div class="row mb-3">
                <div class="col-md-6">
                    <strong>问题:</strong> ${plan.issue || '未指定'}
                </div>
                <div class="col-md-6">
                    <strong>优先级:</strong> <span class="badge bg-primary">${plan.priority || 'medium'}</span>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-md-6">
                    <strong>风险等级:</strong> <span class="badge bg-warning">${plan.risk_level || 'low'}</span>
                </div>
                <div class="col-md-6">
                    <strong>预估时间:</strong> ${plan.estimated_time || '未知'}分钟
                </div>
            </div>
        </div>

        <div class="plan-description mb-4">
            <h6>详细描述</h6>
            <p class="text-muted">${plan.description || '暂无详细描述'}</p>
        </div>

        <div class="plan-commands mb-4">
            <h6>执行命令</h6>
    `;

    if (plan.commands && plan.commands.length > 0) {
        plan.commands.forEach((cmd, index) => {
            detailsHtml += `
                <div class="command-item card mb-2">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span class="badge bg-primary">步骤 ${cmd.step || index + 1}</span>
                        <small>超时: ${cmd.timeout || 30}秒</small>
                    </div>
                    <div class="card-body">
                        <div class="command-description mb-2">
                            <strong>操作:</strong> ${cmd.description || '执行命令'}
                        </div>
                        <div class="command-code">
                            <pre class="bg-dark text-light p-2 rounded"><code>${cmd.command || ''}</code></pre>
                        </div>
                        ${cmd.expected_output ? `
                            <div class="command-expected mt-2">
                                <strong>预期输出:</strong>
                                <pre class="bg-light p-2 rounded small">${cmd.expected_output}</pre>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        });
    } else {
        detailsHtml += '<p class="text-muted">暂无执行命令</p>';
    }

    detailsHtml += `
        </div>

        <div class="plan-rollback mb-4">
            <h6>回滚方案</h6>
    `;

    if (plan.rollback_commands && plan.rollback_commands.length > 0) {
        plan.rollback_commands.forEach((cmd, index) => {
            detailsHtml += `
                <div class="rollback-item card mb-2">
                    <div class="card-header">
                        <span class="badge bg-secondary">回滚步骤 ${cmd.step || index + 1}</span>
                    </div>
                    <div class="card-body">
                        <div class="rollback-description mb-2">
                            <strong>操作:</strong> ${cmd.description || '回滚操作'}
                        </div>
                        <div class="rollback-code">
                            <pre class="bg-dark text-light p-2 rounded"><code>${cmd.command || ''}</code></pre>
                        </div>
                    </div>
                </div>
            `;
        });
    } else {
        detailsHtml += '<p class="text-muted">暂无回滚方案</p>';
    }

    detailsHtml += `
        </div>

        <div class="plan-verification mb-4">
            <h6>验证方案</h6>
    `;

    if (plan.verification_commands && plan.verification_commands.length > 0) {
        plan.verification_commands.forEach((cmd, index) => {
            detailsHtml += `
                <div class="verification-item card mb-2">
                    <div class="card-header">
                        <span class="badge bg-success">验证步骤 ${cmd.step || index + 1}</span>
                    </div>
                    <div class="card-body">
                        <div class="verification-description mb-2">
                            <strong>验证:</strong> ${cmd.description || '验证操作'}
                        </div>
                        <div class="verification-code">
                            <pre class="bg-dark text-light p-2 rounded"><code>${cmd.command || ''}</code></pre>
                        </div>
                        ${cmd.expected_output ? `
                            <div class="verification-expected mt-2">
                                <strong>预期结果:</strong>
                                <pre class="bg-light p-2 rounded small">${cmd.expected_output}</pre>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        });
    } else {
        detailsHtml += '<p class="text-muted">暂无验证方案</p>';
    }

    detailsHtml += '</div>';

    content.innerHTML = detailsHtml;
}

// 批准修复方案
async function approvePlan(planId) {
    if (!confirm('确定要执行此修复方案吗？请仔细检查命令内容。')) {
        return;
    }

    try {
        showNotification('info', '执行方案', '正在执行修复方案...');

        const response = await fetch('/api/fix-plans/approve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ plan_id: planId })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('success', '方案已批准', '修复方案正在执行中...');

            // 在详情区域下方显示执行结果
            showExecutionResultsInDetails(planId, result);

            // 显示执行结果区域
            document.getElementById('executionResultsSection').style.display = 'block';
            document.getElementById('executionStatus').textContent = '执行中';

            // 开始监控执行结果
            monitorExecutionResults(planId);

            // 刷新修复方案状态
            refreshFixPlans();
        } else {
            showNotification('error', '执行失败', result.error || '未知错误');
        }

    } catch (error) {
        showNotification('error', '请求失败', error.message);
    }
}

// 拒绝修复方案
async function rejectPlan(planId) {
    if (!confirm('确定要拒绝此修复方案吗？')) {
        return;
    }

    try {
        const response = await fetch('/api/fix-plans/reject', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ plan_id: planId })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('info', '方案已拒绝', '修复方案已被拒绝');
            refreshFixPlans();
        } else {
            showNotification('error', '操作失败', result.error || '未知错误');
        }

    } catch (error) {
        showNotification('error', '请求失败', error.message);
    }
}

// 从模态框执行方案
async function executePlanFromModal() {
    if (!window.selectedPlanId) {
        showNotification('error', '执行失败', '未选择修复方案');
        return;
    }

    // 关闭模态框
    const modal = bootstrap.Modal.getInstance(document.getElementById('planDetailsModal'));
    modal.hide();

    // 执行方案
    await approvePlan(window.selectedPlanId);
}

// 监控执行结果
async function monitorExecutionResults(planId) {
    const resultsContent = document.getElementById('executionResultsContent');

    // 显示执行中状态
    resultsContent.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">执行中...</span>
            </div>
            <p class="mt-2">正在执行修复方案...</p>
        </div>
    `;

    // 定期检查执行结果
    const checkInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/execution-results?plan_id=${planId}`);
            const result = await response.json();

            if (result.success && result.results) {
                displayExecutionResults(result.results);
                updateExecutionResultsInDetails(planId, result.results);

                // 如果执行完成，停止检查
                if (result.results.completed) {
                    clearInterval(checkInterval);
                    document.getElementById('executionStatus').textContent = '已完成';

                    // 请求AI重新分析
                    requestAIReanalysis(result.results);
                }
            }
        } catch (error) {
            console.error('检查执行结果失败:', error);
        }
    }, 2000);

    // 30秒后自动停止检查
    setTimeout(() => {
        clearInterval(checkInterval);
    }, 30000);
}

// 显示执行结果
function displayExecutionResults(results) {
    const resultsContent = document.getElementById('executionResultsContent');

    let resultsHtml = '<div class="execution-results">';

    if (results.commands && results.commands.length > 0) {
        results.commands.forEach((cmd, index) => {
            const statusClass = cmd.success ? 'success' : 'danger';
            const statusIcon = cmd.success ? '✅' : '❌';

            resultsHtml += `
                <div class="execution-item card mb-2">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span class="badge bg-${statusClass}">${statusIcon} 步骤 ${cmd.step || index + 1}</span>
                        <small class="text-muted">${cmd.execution_time || 0}秒</small>
                    </div>
                    <div class="card-body">
                        <div class="command-executed mb-2">
                            <strong>执行的命令:</strong>
                            <pre class="bg-dark text-light p-2 rounded small">${cmd.command || ''}</pre>
                        </div>
                        ${cmd.output ? `
                            <div class="command-output mb-2">
                                <strong>输出结果:</strong>
                                <pre class="bg-light p-2 rounded small">${cmd.output}</pre>
                            </div>
                        ` : ''}
                        ${cmd.error ? `
                            <div class="command-error text-danger">
                                <strong>错误信息:</strong>
                                <pre class="bg-danger text-light p-2 rounded small">${cmd.error}</pre>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        });
    }

    // 执行总结
    const successCount = results.commands?.filter(cmd => cmd.success).length || 0;
    const totalCount = results.commands?.length || 0;

    resultsHtml += `
        <div class="execution-summary card mt-3">
            <div class="card-header">
                <h6>执行总结</h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <div class="text-center">
                            <h4 class="text-${successCount === totalCount ? 'success' : 'warning'}">
                                ${successCount}/${totalCount}
                            </h4>
                            <small>命令执行成功</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center">
                            <h4 class="text-info">${results.total_time || 0}s</h4>
                            <small>总执行时间</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center">
                            <span class="badge bg-${successCount === totalCount ? 'success' : 'warning'} fs-6">
                                ${successCount === totalCount ? '全部成功' : '部分失败'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    resultsHtml += '</div>';
    resultsContent.innerHTML = resultsHtml;
}

// 请求AI重新分析
async function requestAIReanalysis(executionResults) {
    try {
        showNotification('info', 'AI分析', '正在分析执行结果...');

        const response = await fetch('/api/analyze-execution', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ execution_results: executionResults })
        });

        const result = await response.json();

        if (result.success && result.analysis) {
            showNotification('success', '分析完成', 'AI已分析执行结果');

            // 更新AI建议区域
            if (result.analysis.detected_issues || result.analysis.recommended_actions) {
                displayAISuggestions(result.analysis);
            }

            // 如果有新的修复方案，显示它们
            if (result.analysis.fix_plans && result.analysis.fix_plans.length > 0) {
                console.log('显示新的修复方案:', result.analysis.fix_plans);
                window.currentFixPlans = result.analysis.fix_plans;
                displayFixPlans(result.analysis.fix_plans);

                // 保存到全局变量供后续使用
                window.newFixPlans = result.analysis.fix_plans;

                // 发送新修复方案到后端状态管理器
                fetch('/api/save-fix-plans', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        fix_plans: result.analysis.fix_plans
                    })
                }).catch(err => {
                    console.error('保存新修复方案失败:', err);
                });
            }
        }

    } catch (error) {
        console.error('AI重新分析失败:', error);
    }
}

// 刷新修复方案
async function refreshFixPlans() {
    try {
        const response = await fetch('/api/fix-plans');
        const result = await response.json();

        if (result.success && result.fix_plans) {
            window.currentFixPlans = result.fix_plans;
            displayFixPlans(result.fix_plans);
        }

    } catch (error) {
        console.error('刷新修复方案失败:', error);
    }
}

// 清空执行结果
function clearExecutionResults() {
    const resultsContent = document.getElementById('executionResultsContent');
    resultsContent.innerHTML = `
        <div class="text-center text-muted">
            <i class="fas fa-play-circle fa-2x mb-3"></i>
            <p>暂无执行结果</p>
            <small>执行修复方案后，结果将显示在这里</small>
        </div>
    `;

    document.getElementById('executionResultsSection').style.display = 'none';
    document.getElementById('executionStatus').textContent = '待执行';
}

// 命令编辑功能
function toggleCommandEdit(commandIndex) {
    const displayDiv = document.getElementById(`display-${commandIndex}`);
    const editDiv = document.getElementById(`edit-${commandIndex}`);

    if (editDiv.style.display === 'none') {
        displayDiv.style.display = 'none';
        editDiv.style.display = 'block';
    } else {
        displayDiv.style.display = 'block';
        editDiv.style.display = 'none';
    }
}

function saveCommandEdit(commandIndex) {
    const descInput = document.getElementById(`desc-${commandIndex}`);
    const cmdInput = document.getElementById(`cmd-${commandIndex}`);
    const outputInput = document.getElementById(`output-${commandIndex}`);
    const timeoutInput = document.getElementById(`timeout-${commandIndex}`);

    // 验证输入
    if (!cmdInput.value.trim()) {
        showNotification('error', '错误', '执行命令不能为空');
        return;
    }

    // 更新当前修复方案中的命令
    if (window.currentFixPlans && window.currentFixPlans.length > 0) {
        const currentPlan = window.currentFixPlans.find(p =>
            p.commands && p.commands[commandIndex]
        );

        if (currentPlan && currentPlan.commands) {
            currentPlan.commands[commandIndex] = {
                step: commandIndex + 1,
                description: descInput.value.trim() || '执行命令',
                command: cmdInput.value.trim(),
                expected_output: outputInput.value.trim(),
                timeout: parseInt(timeoutInput.value) || 30
            };

            // 更新显示
            const descSpan = document.querySelector(`[data-command-index="${commandIndex}"] .command-description`);
            if (descSpan) {
                descSpan.textContent = currentPlan.commands[commandIndex].description;
            }

            const codeElement = document.querySelector(`[data-command-index="${commandIndex}"] .command-code code`);
            if (codeElement) {
                codeElement.textContent = currentPlan.commands[commandIndex].command;
            }

            const badgeElement = document.querySelector(`[data-command-index="${commandIndex}"] .badge`);
            if (badgeElement) {
                badgeElement.textContent = `超时: ${currentPlan.commands[commandIndex].timeout}秒`;
            }

            showNotification('success', '保存成功', '命令已更新');
            toggleCommandEdit(commandIndex);
        }
    }
}

function cancelCommandEdit(commandIndex) {
    const descInput = document.getElementById(`desc-${commandIndex}`);
    const cmdInput = document.getElementById(`cmd-${commandIndex}`);
    const outputInput = document.getElementById(`output-${commandIndex}`);
    const timeoutInput = document.getElementById(`timeout-${commandIndex}`);

    if (window.currentFixPlans && window.currentFixPlans.length > 0) {
        const currentPlan = window.currentFixPlans.find(p =>
            p.commands && p.commands[commandIndex]
        );

        if (currentPlan && currentPlan.commands) {
            // 恢复原始值
            const cmd = currentPlan.commands[commandIndex];
            descInput.value = cmd.description || '';
            cmdInput.value = cmd.command || '';
            outputInput.value = cmd.expected_output || '';
            timeoutInput.value = cmd.timeout || 30;
        }
    }

    toggleCommandEdit(commandIndex);
}

// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
    if (websocket) {
        websocket.close();
    }
});

// ==================== 数据库管理功能 ====================

// 数据库管理相关变量
let currentDatabase = null;
let currentTable = null;

// 加载数据库列表
async function loadDatabases() {
    try {
        const response = await fetch('/api/database/databases');
        const data = await response.json();

        if (data.success) {
            const select = document.getElementById('databaseSelect');
            select.innerHTML = '<option value="">请选择数据库...</option>';

            data.databases.forEach(db => {
                const option = document.createElement('option');
                option.value = db;
                option.textContent = db;
                select.appendChild(option);
            });

            showNotification('success', '数据库加载', `成功加载 ${data.databases.length} 个数据库`);
        } else {
            showNotification('error', '加载失败', data.error);
        }
    } catch (error) {
        console.error('加载数据库失败:', error);
        showNotification('error', '网络错误', '无法连接到服务器');
    }
}

// 加载表列表
async function loadTables() {
    const databaseSelect = document.getElementById('databaseSelect');
    const tableSelect = document.getElementById('tableSelect');
    const selectedDatabase = databaseSelect.value;

    currentDatabase = selectedDatabase;

    if (!selectedDatabase) {
        tableSelect.innerHTML = '<option value="">请先选择数据库...</option>';
        return;
    }

    try {
        const response = await fetch(`/api/database/tables?database=${encodeURIComponent(selectedDatabase)}`);
        const data = await response.json();

        if (data.success) {
            tableSelect.innerHTML = '<option value="">请选择表...</option>';

            data.tables.forEach(table => {
                const option = document.createElement('option');
                option.value = table;
                option.textContent = table;
                tableSelect.appendChild(option);
            });

            showNotification('success', '表加载', `数据库 ${selectedDatabase} 中有 ${data.tables.length} 个表`);
        } else {
            showNotification('error', '加载失败', data.error);
        }
    } catch (error) {
        console.error('加载表失败:', error);
        showNotification('error', '网络错误', '无法连接到服务器');
    }
}

// 加载表信息
async function loadTableInfo() {
    const tableSelect = document.getElementById('tableSelect');
    const selectedTable = tableSelect.value;

    currentTable = selectedTable;

    if (!selectedTable || !currentDatabase) {
        hideTableInfo();
        return;
    }

    try {
        const response = await fetch(`/api/database/table-info?database=${encodeURIComponent(currentDatabase)}&table=${encodeURIComponent(selectedTable)}`);
        const data = await response.json();

        if (data.success) {
            displayTableInfo(data.info);
            showNotification('success', '表信息', `成功加载表 ${selectedTable} 的信息`);
        } else {
            showNotification('error', '加载失败', data.error);
        }
    } catch (error) {
        console.error('加载表信息失败:', error);
        showNotification('error', '网络错误', '无法连接到服务器');
    }
}

// 显示表信息
function displayTableInfo(info) {
    const infoDiv = document.getElementById('tableInfo');
    const infoContent = document.getElementById('tableInfoContent');

    infoContent.innerHTML = `
        <div class="table-info">
            <p><strong>表名:</strong> ${info.name}</p>
            <p><strong>数据库:</strong> ${info.database}</p>
            <p><strong>引擎:</strong> ${info.engine || 'N/A'}</p>
            <p><strong>记录数:</strong> ${info.total_count || 0}</p>
            <p><strong>数据大小:</strong> ${formatBytes(info.data_length || 0)}</p>
            <p><strong>索引大小:</strong> ${formatBytes(info.index_length || 0)}</p>
            <p><strong>排序规则:</strong> ${info.collation || 'N/A'}</p>
            <p><strong>备注:</strong> ${info.comment || 'N/A'}</p>
        </div>
    `;

    infoDiv.style.display = 'block';

    // 显示表结构
    displayTableStructure(info.structure);
}

// 显示表结构
function displayTableStructure(structure) {
    const structureDiv = document.getElementById('tableStructure');
    const structureContent = document.getElementById('tableStructureContent');

    if (!structure || structure.length === 0) {
        structureDiv.style.display = 'none';
        return;
    }

    let html = `
        <div class="table-responsive">
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>字段名</th>
                        <th>类型</th>
                        <th>允许空</th>
                        <th>键</th>
                        <th>默认值</th>
                        <th>额外信息</th>
                    </tr>
                </thead>
                <tbody>
    `;

    structure.forEach(col => {
        html += `
            <tr>
                <td><code>${col.field}</code></td>
                <td>${col.type}</td>
                <td>${col.null}</td>
                <td>${col.key || '-'}</td>
                <td>${col.default || '-'}</td>
                <td>${col.extra || '-'}</td>
            </tr>
        `;
    });

    html += '</tbody></table></div>';
    structureContent.innerHTML = html;
    structureDiv.style.display = 'block';
}

// 隐藏表信息
function hideTableInfo() {
    document.getElementById('tableInfo').style.display = 'none';
    document.getElementById('tableStructure').style.display = 'none';
}

// 发送数据库聊天消息
async function sendDatabaseChatMessage() {
    const input = document.getElementById('databaseChatInput');
    const message = input.value.trim();

    if (!message) {
        return;
    }

    // 显示用户消息
    addDatabaseChatMessage('user', message);
    input.value = '';

    // 显示加载状态
    showDatabaseChatStatus(true);

    try {
        const response = await fetch('/api/database/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                database: currentDatabase,
                table: currentTable
            })
        });

        const data = await response.json();

        // 显示AI回复
        addDatabaseChatMessage('assistant', data.response);

        // 显示查询结果
        if (data.sql_result && data.sql_result.success) {
            displayQueryResult(data.sql_result);
        }

        if (data.success) {
            showNotification('success', '查询成功', `意图: ${data.intent_type}`);
        } else {
            showNotification('error', '查询失败', data.error_message);
        }

    } catch (error) {
        console.error('发送消息失败:', error);
        addDatabaseChatMessage('assistant', '抱歉，处理您的请求时发生了错误。');
        showNotification('error', '发送失败', '无法连接到服务器');
    } finally {
        showDatabaseChatStatus(false);
    }
}

// 添加数据库聊天消息
function addDatabaseChatMessage(role, message) {
    const chatHistory = document.getElementById('databaseChatHistory');

    // 如果是第一条消息，清空欢迎信息
    if (chatHistory.querySelector('.text-muted')) {
        chatHistory.innerHTML = '';
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;

    const timestamp = new Date().toLocaleTimeString();

    if (role === 'user') {
        messageDiv.innerHTML = `
            <div class="d-flex justify-content-end mb-2">
                <div class="message-bubble user-bubble">
                    <div class="message-content">${escapeHtml(message)}</div>
                    <div class="message-time">${timestamp}</div>
                </div>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="d-flex justify-content-start mb-2">
                <div class="message-bubble assistant-bubble">
                    <div class="message-content">${message}</div>
                    <div class="message-time">${timestamp}</div>
                </div>
            </div>
        `;
    }

    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// 显示查询结果
function displayQueryResult(result) {
    const resultDiv = document.getElementById('queryResult');
    const resultContent = document.getElementById('queryResultContent');

    if (result.type === 'SELECT' && result.data) {
        let html = `
            <div class="query-stats mb-2">
                <span class="badge bg-info">查询类型: ${result.type}</span>
                <span class="badge bg-success">行数: ${result.row_count}</span>
            </div>
        `;

        if (result.data.length > 0) {
            html += '<div class="table-responsive"><table class="table table-sm table-striped">';

            // 表头
            const columns = result.columns;
            html += '<thead><tr>';
            columns.forEach(col => {
                html += `<th>${col}</th>`;
            });
            html += '</tr></thead><tbody>';

            // 数据行
            result.data.forEach(row => {
                html += '<tr>';
                columns.forEach(col => {
                    const value = row[col];
                    html += `<td>${value !== null ? escapeHtml(String(value)) : '<em>NULL</em>'}</td>`;
                });
                html += '</tr>';
            });

            html += '</tbody></table></div>';
        } else {
            html += '<p class="text-muted">查询结果为空</p>';
        }

        resultContent.innerHTML = html;
    } else if (result.type === 'OTHER') {
        resultContent.innerHTML = `
            <div class="alert alert-success">
                <h6>操作成功</h6>
                <p>${result.message}</p>
            </div>
        `;
    } else {
        resultContent.innerHTML = `
            <div class="alert alert-warning">
                <h6>查询结果</h6>
                <pre>${JSON.stringify(result, null, 2)}</pre>
            </div>
        `;
    }

    resultDiv.style.display = 'block';
}

// 显示/隐藏聊天状态
function showDatabaseChatStatus(show) {
    const statusDiv = document.getElementById('databaseChatStatus');
    statusDiv.style.display = show ? 'block' : 'none';
}

// 清空数据库聊天
function clearDatabaseChat() {
    const chatHistory = document.getElementById('databaseChatHistory');
    chatHistory.innerHTML = `
        <div class="text-muted text-center">
            <i class="fas fa-database fa-3x mb-3"></i>
            <p>使用自然语言描述您的数据库需求</p>
            <small class="text-muted">例如："查询用户表的所有数据" 或 "显示订单表的结构"</small>
        </div>
    `;

    document.getElementById('queryResult').style.display = 'none';
}

// 处理回车键
function handleDatabaseChatKeyPress(event) {
    if (event.key === 'Enter') {
        sendDatabaseChatMessage();
    }
}

// 快捷数据库操作
function quickDatabaseAction(action) {
    const input = document.getElementById('databaseChatInput');

    switch (action) {
        case 'show_tables':
            input.value = '显示所有表';
            break;
        case 'count_records':
            input.value = currentTable ? `${currentTable}表有多少条记录` : '统计记录数';
            break;
        case 'show_schema':
            input.value = currentTable ? `显示${currentTable}表的结构` : '查看表结构';
            break;
        case 'sample_data':
            input.value = currentTable ? `查询${currentTable}表的前10条数据` : '查看示例数据';
            break;
    }

    input.focus();
}

// 格式化字节大小
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// HTML转义
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}