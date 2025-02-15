# OctoBot 中文管理面板

这是一个基于 OctoBot 的中文管理面板，提供了友好的用户界面和完整的交易管理功能。

## 功能特点

- 实时市场数据监控
- 多策略交易管理
- 风险控制系统
- 回测与优化工具
- 完整的用户权限管理
- 中文界面支持

## 系统要求

- Python 3.10+
- Docker
- Git

## 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/JAS888135/lianghcode.git
cd lianghcode
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境：
- 复制 `config/config.example.py` 到 `config/config.py`
- 修改配置文件中的相关设置，包括：
  - SECRET_KEY：修改为随机字符串
  - SMTP配置：用于邮件通知
  - Telegram配置：用于Telegram通知
  - 数据库配置：默认使用SQLite

4. 启动服务：
- Linux/Mac:
```bash
./scripts/start.sh
```
- Windows:
```bash
scripts\start.bat
```

## 项目结构

```
lianghua/
├── app/                    # 主应用目录
│   ├── controllers/       # 控制器
│   ├── models/           # 数据模型
│   ├── templates/        # 模板文件
│   ├── static/           # 静态文件
│   ├── utils/            # 工具函数
│   ├── tasks/            # 后台任务
│   └── services/         # 服务层
├── config/               # 配置文件目录
│   ├── config.example.py # 配置模板
│   └── config.py        # 实际配置文件
├── docker/              # Docker相关文件
│   ├── Dockerfile       # 构建文件
│   └── docker-compose.yml # 容器编排配置
├── logs/                # 日志目录
├── scripts/             # 启动脚本
│   ├── start.sh        # Linux/Mac启动脚本
│   └── start.bat       # Windows启动脚本
├── tentacles/           # OctoBot策略
└── user/                # 用户数据
    ├── config/         # 用户配置
    ├── data/          # 数据文件
    └── profiles/      # 用户配置文件
```

## 配置说明

### 1. 基础配置
在 `config/config.py` 中配置：
- SECRET_KEY：用于会话加密
- 数据库连接
- 日志级别和格式

### 2. 邮件通知
配置SMTP服务器信息：
- SMTP_SERVER
- SMTP_PORT
- SMTP_USERNAME
- SMTP_PASSWORD

### 3. Telegram通知
配置Telegram Bot：
- TELEGRAM_BOT_TOKEN

### 4. 风险控制
在用户界面配置：
- 止损止盈
- 最大持仓
- 风险预警规则

## 使用说明

1. 访问管理面板：
   - 打开浏览器访问 `http://localhost:5001`
   - 默认管理员账号：admin
   - 默认密码：admin

2. 基本配置：
   - 添加交易所API
   - 配置交易策略
   - 设置风险参数

3. 开始交易：
   - 选择交易策略
   - 设置交易参数
   - 启动自动交易

4. 风险管理：
   - 设置全局风险参数
   - 配置交易对特定风险规则
   - 设置预警规则

## 开发计划

详见 [progress.md](progress.md) 文件。

## 常见问题

1. 启动失败
   - 检查配置文件是否正确
   - 检查端口是否被占用
   - 查看日志文件

2. 无法连接交易所
   - 验证API密钥是否正确
   - 检查网络连接
   - 确认IP是否被限制

3. 策略不执行
   - 检查策略配置
   - 验证交易对是否正确
   - 查看日志输出

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 许可证

MIT License 