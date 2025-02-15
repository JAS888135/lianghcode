@echo off

REM 创建必要的目录
mkdir user\config 2>nul
mkdir logs 2>nul
mkdir tentacles 2>nul

REM 停止并删除旧容器
docker-compose down

REM 构建并启动新容器
docker-compose up --build -d

REM 等待服务启动
timeout /t 5

REM 显示容器状态
docker-compose ps

echo OctoBot管理面板已启动，访问地址: http://localhost:5001
pause 