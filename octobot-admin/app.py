from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import docker
import os
from datetime import datetime
import json
import requests
from urllib.parse import urljoin

# Default configurations
default_exchange_config = {
    'exchange': 'binance',
    'trading_type': 'spot',
    'leverage': 1,
    'api_key': '',
    'secret_key': ''
}

# 支持的交易所列表
SUPPORTED_EXCHANGES = [
    'binance',  # 币安
    'huobi',    # 火币
    'okx',      # OKX
    'bybit',    # Bybit
    'gate',     # Gate.io
    'kucoin',   # KuCoin
    'mexc'      # MEXC
]

# 支持的交易对列表
SUPPORTED_TRADING_PAIRS = {
    'USDT': [
        'BTC/USDT',
        'ETH/USDT',
        'BNB/USDT',
        'SOL/USDT',
        'XRP/USDT',
        'ADA/USDT',
        'DOGE/USDT'
    ],
    'USDC': [
        'BTC/USDC',
        'ETH/USDC'
    ],
    'BTC': [
        'ETH/BTC',
        'BNB/BTC'
    ]
}

# 交易所特定的配置
EXCHANGE_SPECIFIC_CONFIG = {
    'binance': {
        'name': 'Binance',
        'supports_spot': True,
        'supports_futures': True,
        'max_leverage': 100,
        'trading_pairs': ['USDT', 'USDC', 'BTC']  # 支持的计价货币
    },
    'huobi': {
        'name': 'Huobi',
        'supports_spot': True,
        'supports_futures': True,
        'max_leverage': 100,
        'trading_pairs': ['USDT', 'USDC']
    },
    'okx': {
        'name': 'OKX',
        'supports_spot': True,
        'supports_futures': True,
        'max_leverage': 100,
        'trading_pairs': ['USDT', 'USDC']
    },
    'bybit': {
        'name': 'Bybit',
        'supports_spot': True,
        'supports_futures': True,
        'max_leverage': 100,
        'trading_pairs': ['USDT', 'USDC']
    },
    'gate': {
        'name': 'Gate.io',
        'supports_spot': True,
        'supports_futures': True,
        'max_leverage': 100,
        'trading_pairs': ['USDT', 'USDC']
    },
    'kucoin': {
        'name': 'KuCoin',
        'supports_spot': True,
        'supports_futures': True,
        'max_leverage': 100,
        'trading_pairs': ['USDT', 'USDC']
    },
    'mexc': {
        'name': 'MEXC',
        'supports_spot': True,
        'supports_futures': True,
        'max_leverage': 100,
        'trading_pairs': ['USDT']
    }
}

default_strategy_config = {
    'trading_pair': 'BTC/USDT',
    'strategy_type': 'dca',
    'dca': {
        'interval': 24,
        'amount': 100
    },
    'grid': {
        'upper_price': 50000,
        'lower_price': 40000,
        'grid_number': 10,
        'total_investment': 1000
    }
}

default_pair_risk_config = {
    'stop_loss': 5,
    'take_profit': 10,
    'max_position': 1,
    'max_trade_amount': 1000
}

# Global variables
config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config'))

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # 用于session
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Docker客户端配置
docker_client = None
try:
    # Windows下尝试通过命名管道连接
    docker_client = docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
    docker_client.ping()
    print("成功通过命名管道连接到Docker")
except Exception as e:
    print(f"命名管道连接失败: {str(e)}")
    try:
        # 尝试默认连接
        docker_client = docker.from_env()
        docker_client.ping()
        print("成功通过默认方式连接到Docker")
    except Exception as e:
        print(f"默认连接失败: {str(e)}")
        try:
            # 尝试TCP连接
            docker_client = docker.DockerClient(base_url='tcp://localhost:2375')
            docker_client.ping()
            print("成功通过TCP连接到Docker")
        except Exception as e:
            print(f"所有Docker连接方式都失败: {str(e)}")
            docker_client = None

# 简单的用户类
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# 用户加载函数
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/')
@login_required
def index():
    status = '未知'
    try:
        if docker_client:
            containers = docker_client.containers.list(all=True, filters={'name': 'OctoBot'})
            if containers:
                container = containers[0]
                container_status = container.status
                print(f"容器状态: {container_status}")
                status = '运行中' if container_status == 'running' else '已停止'
            else:
                print("未找到OctoBot容器")
                status = '未部署'
        else:
            print("Docker客户端未连接")
            status = 'Docker未连接'
    except Exception as e:
        print(f"检查容器状态时出错: {str(e)}")
        status = '未知'
    return render_template('index.html', status=status)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin':
            user = User(username)
            login_user(user, remember=True)  # 添加 remember=True
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('用户名或密码错误')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/control', methods=['POST'])
@login_required
def control():
    action = request.form.get('action')
    try:
        if docker_client:
            containers = docker_client.containers.list(all=True, filters={'name': 'OctoBot'})
            if containers:
                container = containers[0]
                if action == 'start':
                    container.start()
                    flash('OctoBot已启动')
                elif action == 'stop':
                    container.stop()
                    flash('OctoBot已停止')
                elif action == 'restart':
                    container.restart()
                    flash('OctoBot已重启')
            else:
                flash('未找到OctoBot容器')
        else:
            flash('Docker服务未连接')
    except Exception as e:
        flash(f'操作失败: {str(e)}')
    
    return redirect(url_for('index'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        flash('设置已保存')
    return render_template('settings.html')

@app.route('/strategies', methods=['GET', 'POST'])
@login_required
def strategies():
    if request.method == 'POST':
        flash('策略配置已保存')
    return render_template('strategies.html')

@app.route('/trading', methods=['GET', 'POST'])
@login_required
def trading():
    # 初始化配置变量
    exchange_config = default_exchange_config.copy()
    strategy_config = default_strategy_config.copy()
    pair_risk_config = default_pair_risk_config.copy()

    try:
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)

        # 加载配置文件
        exchange_config_path = os.path.join(config_dir, 'exchange_config.json')
        strategy_config_path = os.path.join(config_dir, 'strategy_config.json')
        risk_config_path = os.path.join(config_dir, 'pair_risk_config.json')

        # 加载交易所配置
        if os.path.exists(exchange_config_path):
            try:
                with open(exchange_config_path, 'r') as f:
                    loaded_config = json.load(f)
                    if isinstance(loaded_config, dict):
                        exchange_config.update(loaded_config)
            except Exception as e:
                print(f"加载交易所配置出错: {str(e)}")

        # 加载策略配置
        if os.path.exists(strategy_config_path):
            try:
                with open(strategy_config_path, 'r') as f:
                    loaded_config = json.load(f)
                    if isinstance(loaded_config, dict):
                        strategy_config.update(loaded_config)
            except Exception as e:
                print(f"加载策略配置出错: {str(e)}")

        # 加载风险配置
        if os.path.exists(risk_config_path):
            try:
                with open(risk_config_path, 'r') as f:
                    loaded_config = json.load(f)
                    if isinstance(loaded_config, dict):
                        pair_risk_config.update(loaded_config)
            except Exception as e:
                print(f"加载风险配置出错: {str(e)}")

        # 处理表单提交
        if request.method == 'POST':
            if 'save_exchange' in request.form:
                try:
                    exchange = request.form.get('exchange', 'binance')
                    if exchange not in SUPPORTED_EXCHANGES:
                        raise ValueError('不支持的交易所')

                    trading_type = request.form.get('trading_type', 'spot')
                    if trading_type not in ['spot', 'futures']:
                        raise ValueError('无效的交易类型')

                    # 验证交易所是否支持选择的交易类型
                    exchange_config = EXCHANGE_SPECIFIC_CONFIG.get(exchange, {})
                    if trading_type == 'spot' and not exchange_config.get('supports_spot'):
                        raise ValueError(f'{exchange_config["name"]}不支持现货交易')
                    if trading_type == 'futures' and not exchange_config.get('supports_futures'):
                        raise ValueError(f'{exchange_config["name"]}不支持合约交易')

                    new_config = {
                        'exchange': exchange,
                        'trading_type': trading_type,
                        'api_key': request.form.get('api_key', ''),
                        'secret_key': request.form.get('secret_key', '')
                    }
                    
                    # 如果是合约交易，添加杠杆设置
                    if trading_type == 'futures':
                        leverage = int(request.form.get('leverage', 1))
                        max_leverage = exchange_config.get('max_leverage', 100)
                        if not 1 <= leverage <= max_leverage:
                            raise ValueError(f'杠杆倍数必须在1-{max_leverage}之间')
                        new_config['leverage'] = leverage
                    
                    with open(exchange_config_path, 'w') as f:
                        json.dump(new_config, f, indent=4)
                    exchange_config.update(new_config)
                    flash('交易所配置已保存', 'success')
                except Exception as e:
                    flash(f'保存交易所配置失败: {str(e)}', 'error')
                
            elif 'save_strategy' in request.form:
                try:
                    strategy_type = request.form.get('strategy_type')
                    if strategy_type not in ['dca', 'grid']:
                        raise ValueError('无效的策略类型')
                    
                    trading_pair = request.form.get('trading_pair', '').upper()
                    # 验证交易对格式
                    if not '/' in trading_pair:
                        raise ValueError('无效的交易对格式')
                    base_currency, quote_currency = trading_pair.split('/')
                    
                    # 验证交易对是否在支持列表中
                    supported_pairs = []
                    for pairs in SUPPORTED_TRADING_PAIRS.values():
                        supported_pairs.extend(pairs)
                    if trading_pair not in supported_pairs:
                        # 如果不在支持列表中，检查格式是否正确
                        if not (base_currency.isalnum() and quote_currency.isalnum()):
                            raise ValueError('交易对格式无效')
                        
                    new_config = {
                        'trading_pair': trading_pair,
                        'strategy_type': strategy_type
                    }
                    
                    if strategy_type == 'dca':
                        interval = float(request.form.get('dca_interval', 24))
                        amount = float(request.form.get('dca_amount', 100))
                        if not (1 <= interval <= 168 and amount >= 0.1):
                            raise ValueError('DCA参数超出有效范围')
                        new_config['dca'] = {
                            'interval': interval,
                            'amount': amount
                        }
                    else:  # grid strategy
                        upper_price = float(request.form.get('grid_upper_price', 50000))
                        lower_price = float(request.form.get('grid_lower_price', 40000))
                        grid_number = int(request.form.get('grid_number', 10))
                        total_investment = float(request.form.get('grid_total_investment', 1000))
                        
                        if not (lower_price > 0 and upper_price > lower_price):
                            raise ValueError('网格价格设置无效')
                        if not (3 <= grid_number <= 50):
                            raise ValueError('网格数量必须在3-50之间')
                        if not (total_investment >= 1):
                            raise ValueError('总投资金额必须大于等于1')
                            
                        new_config['grid'] = {
                            'upper_price': upper_price,
                            'lower_price': lower_price,
                            'grid_number': grid_number,
                            'total_investment': total_investment
                        }
                    
                    with open(strategy_config_path, 'w') as f:
                        json.dump(new_config, f, indent=4)
                    strategy_config.update(new_config)
                    flash('策略配置已保存', 'success')
                    
                    # 保存风险配置
                    stop_loss = float(request.form.get('stop_loss', 5))
                    take_profit = float(request.form.get('take_profit', 10))
                    max_position = float(request.form.get('max_position', 1))
                    max_trade_amount = float(request.form.get('max_trade_amount', 1000))
                    
                    if not (0.1 <= stop_loss <= 50):
                        raise ValueError('止损比例超出有效范围(0.1%-50%)')
                    if not (0.1 <= take_profit <= 1000):
                        raise ValueError('止盈比例超出有效范围(0.1%-1000%)')
                    if not (max_position > 0):
                        raise ValueError('最大持仓量必须大于0')
                    if not (max_trade_amount >= 0.1):
                        raise ValueError('单次最大交易额必须大于等于0.1')
                        
                    new_risk_config = {
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'max_position': max_position,
                        'max_trade_amount': max_trade_amount
                    }
                    
                    with open(risk_config_path, 'w') as f:
                        json.dump(new_risk_config, f, indent=4)
                    pair_risk_config.update(new_risk_config)
                    flash('风险控制配置已保存', 'success')
                    
                except ValueError as e:
                    flash(f'参数错误: {str(e)}', 'error')
                except Exception as e:
                    flash(f'保存配置失败: {str(e)}', 'error')
                    
            elif 'start_strategy' in request.form:
                if not exchange_config.get('api_key') or not exchange_config.get('secret_key'):
                    flash('请先配置交易所API密钥', 'error')
                elif not strategy_config.get('trading_pair'):
                    flash('请先配置交易策略', 'error')
                else:
                    mode = request.form.get('start_strategy')
                    if mode == 'simulation':
                        flash('模拟交易已启动', 'success')
                    elif mode == 'real':
                        flash('实盘交易已启动', 'success')
                    else:
                        flash('无效的交易模式', 'error')

    except Exception as e:
        print(f"Trading页面错误: {str(e)}")
        flash(f'加载页面出错: {str(e)}', 'error')

    # 打印调试信息
    print("exchange_config:", exchange_config)
    print("strategy_config:", strategy_config)
    print("pair_risk_config:", pair_risk_config)

    return render_template(
        'trading.html',
        exchange_config=exchange_config,
        strategy_config=strategy_config,
        pair_risk_config=pair_risk_config
    )

@app.route('/api/status')
@login_required
def get_status():
    status = '未知'
    running = False
    try:
        if docker_client:
            containers = docker_client.containers.list(all=True, filters={'name': 'OctoBot'})
            if containers:
                container = containers[0]
                container_status = container.status
                running = container_status == 'running'
                status = '运行中' if running else '已停止'
                print(f"API状态检查 - 容器状态: {container_status}")
            else:
                status = '未部署'
                print("API状态检查 - 未找到OctoBot容器")
        else:
            status = 'Docker未连接'
            print("API状态检查 - Docker客户端未连接")
    except Exception as e:
        print(f"API状态检查出错: {str(e)}")
    
    response = {
        'status': status,
        'running': running
    }
    print(f"API响应: {response}")  # 添加响应日志
    return jsonify(response)

@app.route('/api/trades')
@login_required
def get_trades():
    """
    获取交易记录API
    """
    # TODO: 从数据库或其他数据源获取实际的交易记录
    trades = []
    return jsonify({'trades': trades})

# OctoBot API配置
OCTOBOT_BASE_URL = 'http://localhost:5001'
OCTOBOT_API_BASE = urljoin(OCTOBOT_BASE_URL, '/api/v1/')

def get_octobot_api_url(endpoint):
    return urljoin(OCTOBOT_API_BASE, endpoint)

def call_octobot_api(endpoint, method='GET', data=None):
    """
    调用OctoBot API的通用函数
    """
    url = get_octobot_api_url(endpoint)
    try:
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data)
        else:
            raise ValueError(f'不支持的HTTP方法: {method}')
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"OctoBot API调用失败: {str(e)}")
        return None

@app.route('/api/account')
@login_required
def get_account_info():
    try:
        # 获取OctoBot容器状态
        containers = docker_client.containers.list(all=True, filters={'name': 'OctoBot'})
        if not containers or containers[0].status != 'running':
            return jsonify({
                'error': 'OctoBot容器未运行',
                'total_balance': 0,
                'available_balance': 0,
                'frozen_balance': 0,
                'today_profit': 0,
                'total_profit': 0,
                'balance_change': 0,
                'position_count': 0,
                'order_count': 0,
                'positions': []
            })

        # 从OctoBot API获取账户信息
        account_info = call_octobot_api('portfolio')
        if not account_info:
            return jsonify({'error': 'OctoBot API调用失败'})

        # 解析账户信息
        total_balance = 0
        available_balance = 0
        frozen_balance = 0
        positions = []

        for currency, data in account_info.get('portfolio', {}).items():
            total = float(data.get('total', 0))
            available = float(data.get('free', 0))
            frozen = float(data.get('used', 0))
            
            # 转换为USDT价值
            if currency != 'USDT':
                price_info = call_octobot_api(f'prices/{currency}/USDT')
                if price_info:
                    price = float(price_info.get('price', 0))
                    total_balance += total * price
                    available_balance += available * price
                    frozen_balance += frozen * price
                    
                    if total > 0:
                        positions.append({
                            'symbol': f'{currency}/USDT',
                            'amount': total,
                            'entry_price': price,  # 这里需要从交易历史获取实际的开仓价格
                            'current_price': price,
                            'unrealized_pnl': 0  # 这里需要计算实际的未实现盈亏
                        })
            else:
                total_balance += total
                available_balance += available
                frozen_balance += frozen

        # 获取交易历史计算盈亏
        trades = call_octobot_api('trades')
        today_profit = 0
        total_profit = 0
        if trades:
            # 计算今日和总盈亏
            for trade in trades:
                profit = float(trade.get('profit', 0))
                total_profit += profit
                if trade.get('timestamp', 0) > time.time() - 86400:  # 24小时内
                    today_profit += profit

        response_data = {
            'total_balance': total_balance,
            'available_balance': available_balance,
            'frozen_balance': frozen_balance,
            'today_profit': today_profit,
            'total_profit': total_profit,
            'balance_change': (today_profit / total_balance * 100) if total_balance > 0 else 0,
            'position_count': len(positions),
            'order_count': len(call_octobot_api('orders') or []),
            'positions': positions
        }
        
        return jsonify(response_data)
    except Exception as e:
        print(f"获取账户信息失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/close_position', methods=['POST'])
@login_required
def close_position():
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        
        if not symbol:
            return jsonify({'success': False, 'message': '未提供交易对信息'}), 400
            
        # TODO: 通过OctoBot API发送平仓指令
        # 这里先返回模拟响应
        return jsonify({
            'success': True,
            'message': f'已发送平仓指令: {symbol}'
        })
    except Exception as e:
        print(f"平仓操作失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/manual_trading')
@login_required
def manual_trading():
    """手动交易页面"""
    return render_template('manual_trading.html', trading_pairs=SUPPORTED_TRADING_PAIRS)

@app.route('/api/market_info/<symbol>')
@login_required
def get_market_info(symbol):
    """获取市场信息"""
    try:
        # 验证交易对格式
        if not '/' in symbol:
            return jsonify({'error': '无效的交易对格式'}), 400
            
        base_currency, quote_currency = symbol.split('/')
        
        # 从OctoBot API获取市场数据
        market_data = call_octobot_api(f'prices/{base_currency}/{quote_currency}')
        if not market_data:
            return jsonify({'error': '获取市场数据失败'}), 500

        # 获取24小时价格变化
        price_history = call_octobot_api(f'prices/{base_currency}/{quote_currency}/history')
        price_change = 0
        if price_history:
            current_price = float(market_data.get('price', 0))
            old_price = float(price_history[0].get('price', current_price))
            price_change = ((current_price - old_price) / old_price * 100) if old_price > 0 else 0

        # 获取24小时成交量
        volume = call_octobot_api(f'volume/{base_currency}/{quote_currency}')
        
        response_data = {
            'price': float(market_data.get('price', 0)),
            'change': price_change,
            'volume': f"{volume.get('volume', 0)} {base_currency}" if volume else '0'
        }
        
        return jsonify(response_data)
    except Exception as e:
        print(f"获取市场信息失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/place_order', methods=['POST'])
@login_required
def place_order():
    """下单接口"""
    try:
        data = request.get_json()
        
        # 验证必要字段
        required_fields = ['symbol', 'side', 'order_type', 'amount']
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'message': '缺少必要的订单信息'}), 400
            
        # 验证交易对
        if not '/' in data['symbol']:
            return jsonify({'success': False, 'message': '无效的交易对格式'}), 400
            
        # 验证交易方向
        if data['side'] not in ['buy', 'sell']:
            return jsonify({'success': False, 'message': '无效的交易方向'}), 400
            
        # 验证订单类型
        if data['order_type'] not in ['market', 'limit']:
            return jsonify({'success': False, 'message': '无效的订单类型'}), 400
            
        # 如果是限价单，验证价格
        if data['order_type'] == 'limit' and (not data.get('price') or float(data['price']) <= 0):
            return jsonify({'success': False, 'message': '限价单必须设置有效的价格'}), 400
            
        # 验证数量
        try:
            amount = float(data['amount'])
            if amount <= 0:
                raise ValueError()
        except:
            return jsonify({'success': False, 'message': '无效的交易数量'}), 400
            
        # 如果是合约交易，验证杠杆和保证金类型
        if data.get('trade_type') == 'futures':
            try:
                leverage = int(data.get('leverage', 1))
                if not 1 <= leverage <= 100:
                    return jsonify({'success': False, 'message': '杠杆倍数必须在1-100之间'}), 400
            except:
                return jsonify({'success': False, 'message': '无效的杠杆倍数'}), 400
                
            if data.get('margin_type') not in ['isolated', 'cross']:
                return jsonify({'success': False, 'message': '无效的保证金类型'}), 400

        # 准备订单数据
        order_data = {
            'symbol': data['symbol'],
            'type': data['order_type'],
            'side': data['side'],
            'amount': data['amount']
        }
        
        if data['order_type'] == 'limit':
            order_data['price'] = data['price']
            
        # 如果设置了止损止盈
        if data.get('stop_loss'):
            order_data['stop_loss'] = data['stop_loss']
        if data.get('take_profit'):
            order_data['take_profit'] = data['take_profit']
            
        # 发送订单到OctoBot
        response = call_octobot_api('orders', method='POST', data=order_data)
        if not response:
            return jsonify({'success': False, 'message': '下单失败'}), 500
            
        return jsonify({
            'success': True,
            'message': '订单已提交',
            'order_id': response.get('order_id')
        })
    except Exception as e:
        print(f"下单失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Create default config files if they don't exist
def ensure_config_files():
    # Create config directory if it doesn't exist
    try:
        os.makedirs(config_dir, exist_ok=True)
    except Exception as e:
        print(f"Error creating config directory: {e}")
        return

    config_files = {
        'exchange_config.json': default_exchange_config,
        'strategy_config.json': default_strategy_config,
        'pair_risk_config.json': default_pair_risk_config
    }
    
    for filename, default_config in config_files.items():
        file_path = os.path.join(config_dir, filename)
        try:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                print(f"Created config file: {file_path}")
        except Exception as e:
            print(f"Error creating config file {filename}: {e}")

# Call ensure_config_files() before app.run()
ensure_config_files()

@app.after_request
def add_header(response):
    """
    添加响应头以禁用缓存
    """
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) 