# Makefile for SIDS (Spark-based Intrusion Detection System)

# Node.js 配置 (使用系统全局环境)
NODE := node
NPM := npm

# 默认目标，展示可用命令
help:
	@echo "Usage: make [command]"
	@echo "commands:"
	@echo "  up          - Start all services in detached mode"
	@echo "  down        - Stop and remove all services"
	@echo "  build-ui    - Build the frontend (generate dist/)"
	@echo "  etl         - Run the ETL data processing job"
	@echo "  train       - Run the model training job"
	@echo "  all         - Run the full setup: build-ui -> up -> etl -> train"
	@echo "  logs        - Follow the logs of the web application"
	@echo "  shell       - Get a shell inside the spark container"

# 核心工作流
up:
	docker compose up -d

down:
	docker compose down

build-ui:
	@echo "🔨 构建前端静态资源..."
	@cd web_app/frontend && $(NODE) node_modules/vite/bin/vite.js build
	@echo "✅ 前端构建完成，dist/ 目录已生成。"

etl:
	@./run_etl.sh
	@$(MAKE) fix-perms

# --- 新增：清理模型与大屏缓存文件 ---
clean-models:
	@echo "🧹 正在清理旧模型与前端大屏缓存数据..."
	@rm -f data/models/*.json data/models/*.txt
	@echo "✨ 清理完毕！"

# --- 修改：在执行 train 之前，先自动执行 clean-models ---
train: clean-models
	@./run_train.sh
	@$(MAKE) fix-perms

# 修复宿主机目录权限问题（容器可能以非宿主用户写入文件）
fix-perms:
	@echo "🔧 修复 data 目录权限为当前宿主用户..."
	@chown -R $(shell id -u):$(shell id -g) data || true


all: build-ui up
	@echo "⏳ 等待容器启动..."
	@sleep 10
	@$(MAKE) etl
	@$(MAKE) train

# 辅助命令
logs:
	docker compose logs -f app

shell:
	docker compose exec spark bash

.PHONY: help up down build-ui etl train all logs shell
