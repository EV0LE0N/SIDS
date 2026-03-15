
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, desc, when, sum, length, regexp_extract
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
import json
import os
from datetime import datetime
# 修改点：引用公共配置
from utils import CORE_FEATURES, IDS2018_SCHEMA

def create_spark_session():
    """创建SparkSession实例 (已优化 I/O 配置)"""
    return SparkSession.builder \
        .appName("IDS2018_Clean") \
        .config("spark.driver.memory", "6G") \
        .config("spark.executor.memory", "6G") \
        .config("spark.sql.shuffle.partitions", "10") \
        .config("spark.driver.extraJavaOptions", "-Djava.io.tmpdir=/tmp") \
        .getOrCreate()

def load_data(spark, input_path):
    """最稳逻辑：读取 -> 剥离空格 -> 强转(自动处理非法字符串) -> 填充"""
    # 1. 宽容读取
    df_raw = spark.read.csv(input_path, header=True, inferSchema=False)
  
    # 2. 剥离表头空格（解决原数据集 Bug）
    df_raw = df_raw.toDF(*[c.strip() for c in df_raw.columns])
  
    # 3. 按需提取核心字段
    cols_to_select = CORE_FEATURES + ["Label", "Dst Port"]
    df_selected = df_raw.select(*cols_to_select)
  
    # 4. 【关键修复】放弃 na.replace，直接强转！
    # Spark 的 cast("double") 会自动把 "Infinity", "NaN" 等转为 null
    for col_name in CORE_FEATURES + ["Dst Port"]:
        df_selected = df_selected.withColumn(col_name, col(col_name).cast("double"))
      
    # 5. 统一处理转换后产生的 null 值（原 Infinity/NaN 此时已是 null）
    df_selected = df_selected.fillna(0, subset=CORE_FEATURES)
    
    return df_selected

def clean_data(df, core_cols):
    """数据清洗：异常值处理+零值填充"""
    # 过滤核心字段负数 (修正为 >= 0，保留 0 值)
    for col_name in core_cols:
        df = df.filter(col(col_name) >= 0)
    # 核心字段零值填充
    df = df.fillna(0, subset=core_cols)
    return df

def unify_label(df):
    """标签统一：映射为3大类 (修复混合类型替换 Bug)"""
    # 1. 字典的值必须改为字符串，保证 String -> String 的同构替换
    label_mapping = {
        "Benign": "0",
        "DoS attacks-Hulk": "1",
        "DoS attacks-GoldenEye": "1",
        "DoS attacks-Slowloris": "1",
        "DoS attacks-SlowHTTPTest": "1",
        "FTP-BruteForce": "2",
        "SSH-Bruteforce": "2"
    }
    
    # 2. 执行同构替换（绝对不会报错）
    df = df.replace(label_mapping, subset=["Label"])
    
    # 3. 过滤掉没有匹配上（非 "0", "1", "2"）的无效脏数据
    df = df.filter(col("Label").isin(["0", "1", "2"]))
    
    # 4. 最后统一将 Label 强转为整型，为后续 XGBoost 训练做好准备
    df = df.withColumn("Label", col("Label").cast("integer"))
    
    return df

def precompute_stats(df, output_path):
    """预计算统计指标：攻击类型分布、Top10目标端口"""
    
    # 1. 攻击类型分布
    attack_dist = df.groupBy("Label").count().collect()
    attack_dist_dict = {str(row["Label"]): row["count"] for row in attack_dist}
    
    # 2. Top10目标端口（按双向流量包总数排序：Tot Fwd Pkts + Tot Bwd Pkts）
    # 注意：这里直接使用 Dst Port 进行聚合
    top10_port = df.groupBy("Dst Port") \
        .agg(
            (sum("Tot Fwd Pkts") + sum("Tot Bwd Pkts")).alias("packet_count")
        ) \
        .orderBy(desc("packet_count")) \
        .limit(10) \
        .collect()
    
    # 将浮点数端口（如 80.0）转为整型后再转字符串，优化前端显示
    top10_port_dict = {str(int(row["Dst Port"])): int(row["packet_count"]) for row in top10_port if row["Dst Port"] is not None}
    
    # 3. 构造 stats 字典，确保变量闭环
    stats = {
        "attack_distribution": attack_dist_dict,
        "top10_dst_port": top10_port_dict,  # 这里的 key 从 top10_source_ip 改为了 top10_dst_port
        "stats_metadata": {
            "total_records": df.count(),
            "generated_at": datetime.now().isoformat()
        }
    }
    
    # 保存为JSON（确保目录存在）
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return stats

def save_processed_data(df, output_path):
    """保存清洗后的数据为Parquet格式 (强制合并)"""
    # 注意：不要使用 coalesce(1) 将所有分区拉到单个分区（可能导致 OOM）
    # 让 Spark 写出多个 Parquet 分片，DuckDB 可使用通配符读取：read_parquet('path/*.parquet')
    df.write.mode("overwrite").parquet(output_path)

def main():
    # 配置路径
    input_path = "/app/data/raw/full_data.csv"
    processed_path = "/app/data/processed/attack_data.parquet"
    stats_path = "/app/data/processed/dashboard_stats.json"
    # 使用公共配置的特征列表
    core_cols = CORE_FEATURES
    
    # 执行数据处理流程
    spark = create_spark_session()
    try:
        df_raw = load_data(spark, input_path)
        df_clean = clean_data(df_raw, core_cols)
        df_unified = unify_label(df_clean)
        
        # 注意：数据已在 load_data 阶段完成了按需 select 和 cast("double") 强制类型转换
        # 彻底抛弃了原始 CSV 中的 Timestamp 等多余字段，规避了格式报错
        
        # 【性能优化】缓存中间结果，避免重复扫描
        # 因为后续既要计算统计又要保存Parquet，缓存可避免二次读取1GB数据
        print("正在缓存清洗后的数据以优化性能...")
        df_unified.cache()
        # 触发缓存动作（通过count触发实际缓存）
        total_count = df_unified.count()
        print(f"数据缓存完成，总记录数: {total_count}")
        
        # 预计算统计指标（使用缓存数据）
        precompute_stats(df_unified, stats_path)
        
        # 保存处理后的数据为Parquet格式（使用缓存数据）
        save_processed_data(df_unified, processed_path)
        
        # 清理缓存
        df_unified.unpersist()
        print("数据处理完成！")
    except Exception as e:
        print(f"数据处理失败：{str(e)}")
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
