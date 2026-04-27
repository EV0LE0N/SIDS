# services/db_service.py
# DuckDB 微批落盘服务 — V2.3 架构 第三步
#
# 职责：
#   1. 系统启动时初始化 realtime_logs 表结构
#   2. 接收拼装好预测结果的 Pandas DataFrame，高速批量写入 DuckDB
#
# 设计约束：
#   - DuckDB 连接使用文件模式，写入路径固定为 /app/data/processed/realtime.duckdb
#   - 利用 DuckDB 对 Pandas DataFrame 的零拷贝直接查询能力，不逐行插入
#   - 写入操作是同步的（DuckDB 单连接线程安全，高并发由 FastAPI 的线程池承接）

import logging
import os
import threading

import duckdb
import pandas as pd

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from utils import CORE_FEATURES

logger = logging.getLogger(__name__)

# =============================================================================
# 配置常量
# =============================================================================

DB_PATH = "/app/data/processed/realtime.duckdb"
TABLE_NAME = "realtime_logs"

# DuckDB 连接单例（文件模式，跨请求复用同一连接）
# 使用 threading.Lock 保护并发写入
_conn: duckdb.DuckDBPyConnection | None = None
_lock = threading.Lock()


def _get_conn() -> duckdb.DuckDBPyConnection:
    """懒初始化 DuckDB 文件连接，确保数据目录存在。"""
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _conn = duckdb.connect(DB_PATH)
        logger.info("DuckDB 连接已建立: %s", DB_PATH)
    return _conn


# =============================================================================
# 公开接口
# =============================================================================

def init_db() -> None:
    """
    初始化 realtime_logs 表。
    在 FastAPI lifespan 启动阶段调用，确保表结构就绪后再接受请求。

    表结构：
      - 元数据列：batch_id, timestamp, source_ip
      - 特征列：15 维 CORE_FEATURES（全部 DOUBLE 类型）
      - 预测结果列：attack_type, confidence
    """
    # 动态构建 15 维特征列 DDL，与 CORE_FEATURES 严格对齐
    feature_cols_ddl = ",\n    ".join(
        f'"{feat}" DOUBLE' for feat in CORE_FEATURES
    )

    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        batch_id    VARCHAR,
        timestamp   BIGINT,
        source_ip   VARCHAR,
        {feature_cols_ddl},
        attack_type VARCHAR,
        confidence  DOUBLE
    )
    """

    with _lock:
        conn = _get_conn()
        conn.execute(create_sql)
        logger.info("DuckDB 表 '%s' 已就绪", TABLE_NAME)


def insert_batch(df_batch: pd.DataFrame) -> None:
    """
    将单批次预测结果批量写入 DuckDB。

    利用 DuckDB 直接引用 Pandas DataFrame 变量名（零拷贝）的能力，
    避免将数据序列化为 SQL 字符串，写入效率极高。

    Args:
        df_batch: 包含以下列的 Pandas DataFrame：
                  batch_id, timestamp, source_ip,
                  [15 维 CORE_FEATURES 特征列],
                  attack_type, confidence

    Raises:
        Exception: DuckDB 写入异常时向上透传，由调用方决定是否回滚
    """
    if df_batch.empty:
        logger.warning("insert_batch 收到空 DataFrame，跳过写入")
        return

    try:
        with _lock:
            conn = _get_conn()
            # DuckDB 可以直接在 SQL 中按变量名引用 Pandas DataFrame
            # 此处 df_batch 是局部变量名，DuckDB 自动感知当前作用域
            conn.execute(f"INSERT INTO {TABLE_NAME} SELECT * FROM df_batch")
            logger.debug("写入 %d 条记录到 %s", len(df_batch), TABLE_NAME)
    except Exception as e:
        logger.exception("DuckDB 批量写入失败")
        raise e
