
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, desc, when, sum, length, regexp_extract
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
import json
import os
import glob
from datetime import datetime
# 修改点：引用公共配置
from utils import CORE_FEATURES  # 仅引用常量，Schema 通过 cast("double") 动态处理

def create_spark_session():
    """创建SparkSession实例 (V1.6 优化：防 OOM 配置)"""
    return SparkSession.builder \
        .appName("IDS2018_Clean") \
        .config("spark.driver.memory", "8G") \
        .config("spark.executor.memory", "8G") \
        .config("spark.sql.shuffle.partitions", "200") \
        .config("spark.driver.extraJavaOptions", "-Djava.io.tmpdir=/tmp") \
        .getOrCreate()

def load_data(spark, raw_dir):
    """
    动态对齐读取：逐文件读取并按列名提取，使用 unionByName 拼接
    解决不同日期文件 Schema 列数不一致（如 02-20 有 84 列，其他 80 列）的问题
    """
    csv_files = glob.glob(f"{raw_dir}/*.csv")
    cols_to_select = CORE_FEATURES + ["Label", "Dst Port"]
    final_df = None
    
    for file_path in csv_files:
        print(f"正在读取并对齐: {file_path}")
        df_temp = spark.read.csv(file_path, header=True, inferSchema=False)
        # 剥离表头空格（解决原数据集 Bug）
        df_temp = df_temp.toDF(*[c.strip() for c in df_temp.columns])
        # 按列名提取核心字段，无视列的位置
        df_aligned = df_temp.select(*cols_to_select)
        
        if final_df is None:
            final_df = df_aligned
        else:
            final_df = final_df.unionByName(df_aligned)
    
    # 统一类型转换：所有数值字段强转为 double
    for col_name in CORE_FEATURES + ["Dst Port"]:
        final_df = final_df.withColumn(col_name, col(col_name).cast("double"))
    
    # 填充 null 为 0
    final_df = final_df.fillna(0, subset=CORE_FEATURES)
    
    return final_df

def clean_data(df, core_cols):
    """数据清洗：异常值处理+零值填充"""
    # 过滤核心字段负数 (修正为 >= 0，保留 0 值)
    for col_name in core_cols:
        df = df.filter(col(col_name) >= 0)
    # 核心字段零值填充
    df = df.fillna(0, subset=core_cols)
    return df

def unify_label(df):
    """
    标签统一：映射为3大类 (上帝视角映射)
    宁滥勿缺，确保所有已知攻击类型都能正确映射
    """
    # 1. 完整的攻击类型映射字典
    label_mapping = {
        # 0 类：正常流量
        "Benign": "0",
        
        # 1 类：DoS/DDoS 攻击
        "DoS attacks-Hulk": "1",
        "DoS attacks-GoldenEye": "1",
        "DoS attacks-Slowloris": "1",
        "DoS attacks-SlowHTTPTest": "1",
        "DDoS attacks-LOIC-HTTP": "1",
        "DDOS attack-HOIC": "1",
        "DDOS attack-LOIC-UDP": "1",
        
        # 2 类：暴力破解攻击
        "FTP-BruteForce": "2",
        "SSH-Bruteforce": "2",
        "Brute Force -Web": "2",
        "Brute Force -XSS": "2",
        "SQL Injection": "2"
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
        "top10_dst_port": top10_port_dict,
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
    raw_dir = "/app/data/raw"
    processed_path = "/app/data/processed/attack_data.parquet"
    stats_path = "/app/data/processed/dashboard_stats.json"
    # 使用公共配置的特征列表
    core_cols = CORE_FEATURES
  
    # 执行数据处理流程
    spark = create_spark_session()
    try:
        df_raw = load_data(spark, raw_dir)
        df_clean = clean_data(df_raw, core_cols)
        df_unified = unify_label(df_clean)
      
        # 注意：数据已在 load_data 阶段完成了按需 select 和 cast("double") 强制类型转换
        # 彻底抛弃了原始 CSV 中的 Timestamp 等多余字段，规避了格式报错
      
        # V1.6 核心修改：删除 cache() 逻辑，牺牲几分钟 CPU 时间换取内存绝对安全
        # 原因：15 个特征的 1500 万行数据无法塞进 8G 内存，cache() 会导致 OOM
        print("跳过内存缓存阶段，采用流式计算以防 OOM...")
      
        # 预计算统计指标（会触发一次 Action）
        print("正在计算可视化统计指标...")
        precompute_stats(df_unified, stats_path)
      
        # 保存处理后的数据为Parquet格式（会触发第二次 Action）
        print("正在持久化 Parquet 数据分片...")
        save_processed_data(df_unified, processed_path)
      
        print("数据处理完成！")
    except Exception as e:
        print(f"数据处理失败：{str(e)}")
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
