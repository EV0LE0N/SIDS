
#!/bin/bash
echo "🚀 开始执行模型训练任务..."
# 训练脚本使用原生Python运行，复用Web容器的Python环境（已安装xgboost/pandas/duckdb等依赖）
docker compose exec app python /app/spark_jobs/train_model.py
echo "✅ 模型训练任务执行完毕。xgb_model.json 已生成。"
