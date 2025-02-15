// 全局变量
const API_BASE_URL = '/api';
let websocket = null;

// 工具函数
const formatNumber = (number, decimals = 2) => {
    return Number(number).toFixed(decimals);
};

const formatDate = (date) => {
    return new Date(date).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
};

const showAlert = (message, type = 'success') => {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    $('#alerts-container').append(alertHtml);
    
    // 5秒后自动关闭
    setTimeout(() => {
        $('.alert').alert('close');
    }, 5000);
};

// API 请求函数
const apiRequest = async (endpoint, options = {}) => {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        showAlert(error.message, 'danger');
        throw error;
    }
};

// WebSocket 连接
const initWebSocket = () => {
    if (websocket) {
        websocket.close();
    }
    
    websocket = new WebSocket(`ws://${window.location.host}/ws`);
    
    websocket.onopen = () => {
        console.log('WebSocket connected');
        showAlert('实时数据连接已建立', 'info');
    };
    
    websocket.onclose = () => {
        console.log('WebSocket disconnected');
        // 5秒后尝试重连
        setTimeout(initWebSocket, 5000);
    };
    
    websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        showAlert('实时数据连接出错', 'danger');
    };
    
    websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
};

// WebSocket 消息处理
const handleWebSocketMessage = (data) => {
    switch (data.type) {
        case 'price_update':
            updatePriceDisplay(data);
            break;
        case 'trade_update':
            updateTradeHistory(data);
            break;
        case 'portfolio_update':
            updatePortfolio(data);
            break;
        case 'notification':
            handleNotification(data);
            break;
        default:
            console.log('Unknown message type:', data.type);
    }
};

// 价格更新
const updatePriceDisplay = (data) => {
    const priceElement = $(`#price-${data.symbol}`);
    const oldPrice = parseFloat(priceElement.text());
    const newPrice = parseFloat(data.price);
    
    priceElement.text(formatNumber(newPrice));
    priceElement.removeClass('price-up price-down');
    
    if (newPrice > oldPrice) {
        priceElement.addClass('price-up');
    } else if (newPrice < oldPrice) {
        priceElement.addClass('price-down');
    }
};

// 交易历史更新
const updateTradeHistory = (data) => {
    const tradeRow = `
        <tr>
            <td>${formatDate(data.timestamp)}</td>
            <td>${data.symbol}</td>
            <td>${data.side}</td>
            <td>${formatNumber(data.amount)}</td>
            <td>${formatNumber(data.price)}</td>
            <td><span class="status-badge status-${data.status.toLowerCase()}">${data.status}</span></td>
        </tr>
    `;
    
    $('#trade-history tbody').prepend(tradeRow);
    
    // 保持最新的 50 条记录
    if ($('#trade-history tbody tr').length > 50) {
        $('#trade-history tbody tr:last').remove();
    }
};

// 资产组合更新
const updatePortfolio = (data) => {
    data.assets.forEach(asset => {
        const row = $(`#asset-${asset.symbol}`);
        if (row.length) {
            row.find('.asset-amount').text(formatNumber(asset.amount));
            row.find('.asset-value').text(formatNumber(asset.value));
            
            const changeElement = row.find('.asset-change');
            changeElement.text(formatNumber(asset.change_24h) + '%');
            changeElement.removeClass('text-success text-danger');
            changeElement.addClass(asset.change_24h >= 0 ? 'text-success' : 'text-danger');
        }
    });
    
    // 更新总资产价值
    $('#total-portfolio-value').text(formatNumber(data.total_value));
    $('#portfolio-change').text(formatNumber(data.total_change_24h) + '%');
};

// 通知处理
const handleNotification = (data) => {
    const notificationHtml = `
        <div class="notification-item ${data.read ? '' : 'unread'}">
            <h6 class="notification-title">${data.title}</h6>
            <p class="notification-message">${data.message}</p>
            <small class="notification-time">${formatDate(data.timestamp)}</small>
        </div>
    `;
    
    $('.notification-list').prepend(notificationHtml);
    
    // 更新未读通知数量
    const unreadCount = $('.notification-item.unread').length;
    $('#notification-badge').text(unreadCount);
    
    if (!data.read) {
        showAlert(data.title, 'info');
    }
};

// 表单验证
const validateForm = (formId) => {
    const form = $(`#${formId}`);
    if (!form[0].checkValidity()) {
        form[0].reportValidity();
        return false;
    }
    return true;
};

// 页面加载完成后初始化
$(document).ready(() => {
    // 初始化 Bootstrap 工具提示
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // 初始化 WebSocket 连接
    if ($('#real-time-data').length) {
        initWebSocket();
    }
    
    // 表单提交处理
    $('form').on('submit', async function(e) {
        e.preventDefault();
        
        if (!validateForm(this.id)) {
            return;
        }
        
        const formData = new FormData(this);
        const jsonData = {};
        formData.forEach((value, key) => {
            jsonData[key] = value;
        });
        
        try {
            const response = await apiRequest(this.action, {
                method: 'POST',
                body: JSON.stringify(jsonData)
            });
            
            showAlert(response.message || '操作成功');
            
            // 根据表单 ID 执行特定操作
            switch (this.id) {
                case 'login-form':
                    window.location.href = '/dashboard';
                    break;
                case 'register-form':
                    window.location.href = '/login';
                    break;
                default:
                    this.reset();
            }
        } catch (error) {
            // 错误已在 apiRequest 中处理
        }
    });
    
    // 暗色模式切换
    $('#dark-mode-toggle').on('click', function() {
        $('body').toggleClass('dark-mode');
        const isDarkMode = $('body').hasClass('dark-mode');
        localStorage.setItem('darkMode', isDarkMode);
        $(this).find('i').toggleClass('bi-moon bi-sun');
    });
    
    // 加载保存的暗色模式设置
    if (localStorage.getItem('darkMode') === 'true') {
        $('body').addClass('dark-mode');
        $('#dark-mode-toggle i').removeClass('bi-moon').addClass('bi-sun');
    }
});

// 图表相关函数
const createChart = (containerId, type, data, options = {}) => {
    const ctx = document.getElementById(containerId).getContext('2d');
    return new Chart(ctx, {
        type: type,
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            ...options
        }
    });
};

// 策略相关函数
const startStrategy = async (strategyId) => {
    try {
        const response = await apiRequest(`/strategy/${strategyId}/start`, {
            method: 'POST'
        });
        showAlert(response.message);
        updateStrategyStatus(strategyId, 'active');
    } catch (error) {
        // 错误已在 apiRequest 中处理
    }
};

const stopStrategy = async (strategyId) => {
    try {
        const response = await apiRequest(`/strategy/${strategyId}/stop`, {
            method: 'POST'
        });
        showAlert(response.message);
        updateStrategyStatus(strategyId, 'inactive');
    } catch (error) {
        // 错误已在 apiRequest 中处理
    }
};

const updateStrategyStatus = (strategyId, status) => {
    const statusBadge = $(`#strategy-${strategyId} .strategy-status`);
    statusBadge.removeClass('status-active status-inactive status-warning status-danger');
    statusBadge.addClass(`status-${status}`);
    statusBadge.text(status.charAt(0).toUpperCase() + status.slice(1));
};

// 导出函数
window.startStrategy = startStrategy;
window.stopStrategy = stopStrategy; 