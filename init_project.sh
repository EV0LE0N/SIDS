#!/bin/bash

# ==========================================
# SIDS 项目初始化脚本 (V1.2 极简版)
# 适用环境：macOS (M2) + OrbStack
# 核心逻辑：硬编码 501:20 权限，彻底消除权限冲突
# ==========================================

echo "🚀 开始搭建 SIDS 项目骨架..."

# 1. 定义需要创建的目录树
DIRS=(
    "data/raw"
    "data/processed"
    "data/models"
    "spark_jobs"
    "web_app/backend/routers"
    "web_app/backend/services"
    "web_app/frontend/dist"
    "web_app/frontend/public"
    "web_app/frontend/src/api"
    "web_app/frontend/src/components/common"
    "web_app/frontend/src/components/dashboard"
    "web_app/frontend/src/router"
    "web_app/frontend/src/views"
)

# 2. 循环创建目录并放置 .gitkeep
# 这是为了防止 Git 忽略空目录，确保项目结构在任何地方都一致
for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        touch "$dir/.gitkeep"
        echo "  ✅ 已创建目录并初始化: $dir"
    else
        echo "  🟡 目录已存在，跳过: $dir"
    fi
done

# 3. 核心步骤：权限对齐
# 直接将当前目录下所有文件所有权移交给你的 Mac 用户 (501:staff)
echo "🔒 正在执行权限对齐 (Target: 501:20)..."
chown -R 501:20 .
chmod -R 755 .

echo "------------------------------------------"
echo "🎉 恭喜！项目骨架已就绪。"
echo "💡 下一步建议：将你的 compose.yml 放入根目录，然后尝试执行 docker compose up -d"
echo "------------------------------------------"