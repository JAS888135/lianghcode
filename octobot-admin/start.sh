#!/bin/bash

# 创建必要的目录
mkdir -p user/config logs tentacles

# 停止并删除旧容器
docker-compose down

# 构建并启动新容器
docker-compose up --build -d

# 等待服务启动
sleep 5

# 显示容器状态
docker-compose ps

echo "OctoBot管理面板已启动，访问地址: http://localhost:5001" 