
# 公共工具模块
# 作用：统一数据清洗逻辑与特征配置，消除训练-推理偏差
import pandas as pd
import numpy as np
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

# 核心特征清单：定义模型唯一认可的输入维度（严格对齐真实 CSV 表头缩写）
CORE_FEATURES = [
    "Flow Duration", "Tot Fwd Pkts", "Tot Bwd Pkts",
    "TotLen Fwd Pkts", "TotLen Bwd Pkts",
    "Fwd Pkt Len Max", "Fwd Pkt Len Min",
    "Fwd Pkt Len Mean", "Flow Byts/s", "Flow Pkts/s"
]
LABEL_COL = "Label"

# 显式 Schema：解决 inferSchema 性能瓶颈与类型推断错误
IDS2018_SCHEMA = StructType([
    *[StructField(f, DoubleType(), True) for f in CORE_FEATURES],
    StructField(LABEL_COL, StringType(), True)
])

def clean_data_logic(df_pandas):
    """
    统一清洗逻辑，供 ETL (Spark转Pandas逻辑) 和 API (单条预测) 复用
    注意：输入必须是 Pandas DataFrame 或 字典
    """
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
