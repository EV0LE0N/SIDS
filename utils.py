
# utils.py
# 公共工具模块 - 跨容器共享配置
# 重要：所有容器依赖的第三方库必须使用懒加载模式，避免跨容器依赖泄露

# 核心特征清单：定义模型唯一认可的输入维度（严格对齐真实 CSV 表头缩写）
CORE_FEATURES = [
    "Flow Duration", "Tot Fwd Pkts", "Tot Bwd Pkts",
    "TotLen Fwd Pkts", "TotLen Bwd Pkts",
    "Fwd Pkt Len Max", "Fwd Pkt Len Min",
    "Fwd Pkt Len Mean", "Flow Byts/s", "Flow Pkts/s",
    "Bwd Pkt Len Max", "Bwd Pkt Len Min", "Bwd Pkt Len Mean",
    "Flow IAT Mean", "Flow IAT Max"
]
LABEL_COL = "Label"

def get_spark_schema():
    """
    懒加载模式：仅当 Spark 容器调用此函数时，才会真正导入 pyspark 依赖
    解决 Web 容器 (无 pyspark 环境) 导入 utils.py 时的 ModuleNotFoundError 报错
    """
    from pyspark.sql.types import StructType, StructField, StringType, DoubleType
    
    return StructType([
        *[StructField(f, DoubleType(), True) for f in CORE_FEATURES],
        StructField(LABEL_COL, StringType(), True)
    ])

def clean_data_logic(df_pandas):
    """
    统一清洗逻辑，供 ETL (Spark转Pandas逻辑) 和 API (单条预测) 复用
    注意：输入必须是 Pandas DataFrame 或 字典
    """
    import pandas as pd
    import numpy as np
    # 1. 处理无穷大与非法字符串，防止推理阶段崩溃
    df_pandas = df_pandas.replace(
        [np.inf, -np.inf, "Infinity", "NaN", "inf", "-inf"],
        0
    )
    # 2. 填充空值
    df_pandas = df_pandas.fillna(0)
    # 3. 强制类型转换 (防止入模报错)
    for col in CORE_FEATURES:
        if col in df_pandas.columns:
            df_pandas[col] = pd.to_numeric(df_pandas[col], errors='coerce').fillna(0)
    return df_pandas
