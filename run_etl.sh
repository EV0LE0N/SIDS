
#!/bin/bash
echo "🚀 开始执行 ETL 数据处理任务..."
docker compose exec spark /opt/spark/bin/spark-submit \
    --master local[*] \
    --conf spark.driver.extraJavaOptions="-Djava.io.tmpdir=/tmp" \
    /app/spark_jobs/etl_clean.py
echo "✅ ETL 任务执行完毕。"
