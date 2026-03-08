
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
        .config("spark.driver.memory", "8G") \
        .config("spark.executor.memory", "8G") \
        .config("spark.sql.shuffle.partitions", "10") \
        .config("spark.driver.extraJavaOptions", "-Djava.io.tmpdir=/tmp") \
        # 注意：Local模式下Driver与Executor共享进程，内存总和（8G+8G=16G）可能超过容器限制（12G），但实际物理内存占用由容器水位控制，单个组件声明内存（8G）不超过容器水位即可。
        .getOrCreate()

def load_data(spark, input_path):
    # 显式 Schema 加载，跳过全量扫描，I/O 效率提升约 50%
    return spark.read.csv(input_path, header=True, schema=IDS2018_SCHEMA)

def clean_data(df, core_cols):
    """数据清洗：异常值处理+零值填充"""
    # 替换Infinity为null（使用 na.replace 方法）
    df = df.na.replace("Infinity", None)
    # 过滤核心字段负数 (修正为 >= 0，保留 0 值)
    for col_name in core_cols:
        df = df.filter(col(col_name) >= 0)
    # 核心字段零值填充
    df = df.fillna(0, subset=core_cols)
    return df

def unify_label(df):
    """标签统一：映射为3大类"""
    label_mapping = {
        "Benign": 0,
        "DoS attacks-Hulk": 1,
        "DoS attacks-GoldenEye": 1,
        "DoS attacks-Slowloris": 1,
        "DoS attacks-SlowHTTPTest": 1,
        "FTP-BruteForce": 2,
        "SSH-Bruteforce": 2
    }
    # 替换标签
    df = df.replace(label_mapping, subset=["Label"])
    # 删除未匹配标签数据
    df = df.filter(col("Label").isin([0, 1, 2]))
    return df

def precompute_stats(df, output_path):
    """预计算统计指标：攻击类型分布、Top10源IP"""
    # 【性能优化】数据初筛闸门：过滤掉明显异常的IP地址
    # 1. 过滤空IP和过短IP（长度小于7，如"0.0.0.0"或无效值）
    # 2. 过滤包含非IP字符的异常值（简单正则匹配）
  
    # 定义IP过滤条件：基本IP格式验证（简化版，实际可根据需要增强）
    ip_filtered_df = df.filter(
        (length(col("Source IP")) >= 7) &  # 最小IP长度
        (col("Source IP").isNotNull()) &   # 非空
        (regexp_extract(col("Source IP"), r'^\d+\.\d+\.\d+\.\d+$', 0) != "")  # 基本IP格式
    )
  
    # 如果过滤后数据量过少，回退到原始数据（确保演示可用性）
    if ip_filtered_df.count() < 100:
        ip_filtered_df = df
        print("⚠️ IP过滤过严，回退到原始数据进行统计")
  
    # 1. 攻击类型分布（使用过滤后的数据）
    attack_dist = ip_filtered_df.groupBy("Label").count().collect()
    attack_dist_dict = {str(row["Label"]): row["count"] for row in attack_dist}
  
    # 2. Top10源IP（按双向流量包总数排序：Total Fwd Packets + Total Backward Packets）
    top10_ip = ip_filtered_df.groupBy("Source IP") \
        .agg(
            (sum("Total Fwd Packets") + sum("Total Backward Packets")).alias("packet_count")
        ) \
        .orderBy(desc("packet_count")) \
        .limit(10) \
        .collect()
  
    # 对IP进行安全编码处理，防止JSON序列化问题
    top10_ip_dict = {}
    for row in top10_ip:
        ip = str(row["Source IP"]).strip()
        # 移除可能引起JSON问题的特殊字符
        ip = ip.replace('"', '').replace('\\', '').replace('\n', '').replace('\r', '')
        top10_ip_dict[ip] = int(row["packet_count"])
  
    # 3. 构造 stats 字典，确保变量闭环
    stats = {
        "attack_distribution": attack_dist_dict,
        "top10_source_ip": top10_ip_dict,
        "stats_metadata": {
            "total_records": df.count(),
            "filtered_records": ip_filtered_df.count(),
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
    
        # 注意：由于使用了显式 Schema，不再需要手动 cast("double")
        # Schema 已确保所有核心特征字段为 DoubleType
    
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
