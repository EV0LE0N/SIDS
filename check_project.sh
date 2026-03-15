#!/bin/bash

# ==========================================
# SIDS 项目完整性检查脚本
# 检查项目结构、文件完整性和配置正确性
# ==========================================

echo "🔍 开始检查 SIDS 项目完整性..."
echo "=========================================="

# 1. 检查目录结构
echo "1. 检查目录结构..."
REQUIRED_DIRS=(
    "data/raw"
    "data/processed"
    "data/models"
    "spark_jobs"
    "web_app/backend/routers"
    "web_app/backend/services"
    "web_app/frontend/src/api"
    "web_app/frontend/src/components/common"
    "web_app/frontend/src/components/dashboard"
    "web_app/frontend/src/router"
    "web_app/frontend/src/views"
)

all_dirs_ok=true
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir"
    else
        echo "  ❌ $dir (缺失)"
        all_dirs_ok=false
    fi
done

echo ""

# 2. 检查关键文件
echo "2. 检查关键文件..."
REQUIRED_FILES=(
    "compose.yml"
    "Dockerfile"
    "Makefile"
    "nginx.conf"
    "requirements.txt"
    "utils.py"
    "run_etl.sh"
    "run_train.sh"
    "spark_jobs/etl_clean.py"
    "spark_jobs/train_model.py"
    "web_app/backend/main.py"
    "web_app/backend/requirements.txt"
    "web_app/backend/routers/stats.py"
    "web_app/backend/routers/predict.py"
    "web_app/backend/services/model_service.py"
    "web_app/frontend/package.json"
    "web_app/frontend/vite.config.js"
    "web_app/frontend/src/main.js"
    "web_app/frontend/src/App.vue"
    "web_app/frontend/src/views/Dashboard.vue"
    "web_app/frontend/src/views/Detect.vue"
    "web_app/frontend/src/api/stats.js"
    "web_app/frontend/src/api/predict.js"
    "web_app/frontend/src/router/index.js"
    "web_app/frontend/public/index.html"
)

all_files_ok=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (缺失)"
        all_files_ok=false
    fi
done

echo ""

# 3. 检查数据文件
echo "3. 检查数据文件..."
if [ -f "data/raw/full_data.csv" ]; then
    echo "  ✅ data/raw/full_data.csv (原始数据)"
    # 检查文件大小
    file_size=$(stat -f%z "data/raw/full_data.csv" 2>/dev/null || stat -c%s "data/raw/full_data.csv" 2>/dev/null)
    if [ $file_size -gt 100000000 ]; then  # 大于100MB
        echo "    📊 文件大小: $(($file_size/1024/1024))MB"
    else
        echo "    ⚠️  文件大小: $(($file_size/1024))KB (可能不是完整数据集)"
    fi
else
    echo "  ⚠️  data/raw/full_data.csv (缺失 - 需要放置原始数据)"
    # 检查是否有其他CSV文件
    csv_count=$(find data/raw -name "*.csv" -type f | wc -l)
    if [ $csv_count -gt 0 ]; then
        echo "    📁 找到 $csv_count 个CSV文件，可重命名为 full_data.csv"
    fi
fi

echo ""

# 4. 检查配置文件内容
echo "4. 检查配置文件内容..."

# 检查Dockerfile
if grep -q "FROM python:3.10" Dockerfile 2>/dev/null; then
    echo "  ✅ Dockerfile 使用正确的Python版本"
else
    echo "  ❌ Dockerfile Python版本不正确"
fi

# 检查requirements.txt
if [ -f "requirements.txt" ]; then
    req_count=$(wc -l < requirements.txt)
    echo "  ✅ requirements.txt 包含 $req_count 个依赖"
fi

# 检查compose.yml服务
if grep -q "services:" compose.yml 2>/dev/null; then
    service_count=$(grep -c "^  [a-z]" compose.yml 2>/dev/null || echo "0")
    echo "  ✅ compose.yml 包含 $service_count 个服务"
fi

echo ""

# 5. 检查权限
echo "5. 检查脚本权限..."
SCRIPTS=("run_etl.sh" "run_train.sh" "check_project.sh")
for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ] && [ -x "$script" ]; then
        echo "  ✅ $script 可执行"
    elif [ -f "$script" ]; then
        echo "  ⚠️  $script 不可执行 (运行: chmod +x $script)"
    fi
done

echo ""
echo "=========================================="

# 总结
if $all_dirs_ok && $all_files_ok; then
    echo "🎉 项目结构完整！可以开始部署。"
    echo ""
    echo "下一步建议："
    echo "1. 确保 data/raw/full_data.csv 存在（完整数据集）"
    echo "2. 运行: make all 一键部署"
    echo "3. 或分步执行:"
    echo "   - make build-ui  # 构建前端"
    echo "   - make up        # 启动容器"
    echo "   - make etl       # 数据处理"
    echo "   - make train     # 模型训练"
else
    echo "⚠️  项目结构不完整，请修复缺失的文件和目录。"
    echo ""
    echo "缺失的文件可能需要从 sids_V1.3.md 文档中复制代码创建。"
fi

echo "=========================================="