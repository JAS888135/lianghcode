# 邮件配置
SMTP_SERVER = 'smtp.gmail.com'  # 邮件服务器
SMTP_PORT = 587  # 邮件服务器端口
SMTP_USERNAME = 'your-email@gmail.com'  # 邮箱账号
SMTP_PASSWORD = 'your-app-password'  # 邮箱密码或应用专用密码
MAIL_SENDER = 'OctoBot Alert <your-email@gmail.com>'  # 发件人

# Telegram配置
TELEGRAM_BOT_TOKEN = 'your-bot-token'  # Telegram机器人Token

# 预警检查配置
ALERT_CHECK_INTERVAL = 60  # 预警检查间隔（秒）
MAX_ALERTS_PER_HOUR = 10  # 每小时最大预警次数
ALERT_COOLDOWN = 3600  # 相同预警的冷却时间（秒） 