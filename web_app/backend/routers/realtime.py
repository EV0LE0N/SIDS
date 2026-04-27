# routers/realtime.py
# 实时检测微批处理 API 模块 (V2.3 架构)
# 本轮更新：接入真实 XGBoost 推理 + DuckDB 微批落盘 + WebSocket 实时广播

import asyncio
import logging
from typing import List

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator, model_validator

# 从公共配置引用核心常量，禁止在本模块中硬编码分类字符串
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from utils import CORE_FEATURES, ATTACK_LABEL_MAP

from services.model_service import batch_predict
from services import db_service
from services.ws_manager import manager as ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# Pydantic 数据模型定义
# =============================================================================

class FeatureRecord(BaseModel):
    """单条流量记录：来源 IP + 15 维核心特征向量"""
    source_ip: str
    features: dict

    @field_validator("features")
    @classmethod
    def validate_features(cls, v: dict) -> dict:
        """
        严格校验特征字典：
        1. 确保所有 CORE_FEATURES 中的键都存在（禁止特征缺失）
        2. 确保所有值都可以转换为浮点数（禁止类型错误）
        """
        missing_keys = [k for k in CORE_FEATURES if k not in v]
        if missing_keys:
            raise ValueError(
                f"特征字段缺失，共缺少 {len(missing_keys)} 个: {missing_keys}"
            )

        for key, val in v.items():
            if key not in CORE_FEATURES:
                # 忽略 CORE_FEATURES 之外的多余字段（防御性设计）
                continue
            try:
                float(val)
            except (TypeError, ValueError):
                raise ValueError(
                    f"特征 '{key}' 的值 '{val}' 无法转换为浮点数"
                )

        return v


class BatchPredictRequest(BaseModel):
    """微批预测请求体"""
    batch_id: str           # 批次唯一标识（由仿真层生成）
    timestamp: int          # Unix 时间戳（整型秒）
    records: List[FeatureRecord]

    @model_validator(mode="after")
    def validate_records_not_empty(self) -> "BatchPredictRequest":
        if not self.records:
            raise ValueError("records 列表不能为空")
        return self


class PredictResultItem(BaseModel):
    """单条预测结果"""
    ip: str
    attack_type: str        # 取值动态来自 ATTACK_LABEL_MAP.values()，禁止硬编码
    confidence: float


class BatchPredictResponse(BaseModel):
    """微批预测响应体"""
    batch_id: str
    results: List[PredictResultItem]


# =============================================================================
# API 路由实现
# =============================================================================

@router.post(
    "/realtime/predict-batch",
    response_model=BatchPredictResponse,
    summary="微批实时攻击检测",
    description="接收仿真层批量流量特征，调用 XGBoost 推理并写入 DuckDB，返回每条记录的攻击类型与置信度。",
)
async def predict_batch(request: BatchPredictRequest) -> BatchPredictResponse:
    """
    微批预测接口核心逻辑：
    1. 从请求体提取特征字典，按 CORE_FEATURES 顺序构建 DataFrame（严格对齐，防列错位）
    2. 调用 batch_predict() 获得真实 XGBoost 推理结果
    3. 拼装完整记录（元数据 + 特征 + 预测结果）写入 DuckDB
    4. 组装并返回 BatchPredictResponse
    """
    # --- Step 1: 构建特征矩阵 ---
    try:
        feature_rows = []
        for record in request.records:
            row = {feat: float(record.features[feat]) for feat in CORE_FEATURES}
            feature_rows.append(row)

        df_features = pd.DataFrame(feature_rows, columns=CORE_FEATURES)

    except KeyError as e:
        logger.error("特征提取时发生 KeyError: %s", e)
        raise HTTPException(status_code=400, detail=f"特征字段缺失: {e}")
    except (ValueError, TypeError) as e:
        logger.error("特征类型转换失败: %s", e)
        raise HTTPException(status_code=400, detail=f"特征数据类型错误: {e}")
    except Exception as e:
        logger.exception("构建特征矩阵时发生未知异常")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

    # --- Step 2: XGBoost 推理 ---
    try:
        predictions = batch_predict(df_features)
    except RuntimeError as e:
        # 模型未加载（xgb_model.json 不存在）
        logger.error("模型不可用: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("推理阶段发生异常")
        raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")

    # --- Step 3: 拼装完整 DataFrame 并落盘 DuckDB ---
    try:
        df_log = df_features.copy()
        # 在特征 DataFrame 前插入元数据列
        df_log.insert(0, "source_ip", [r.source_ip for r in request.records])
        df_log.insert(0, "timestamp", request.timestamp)
        df_log.insert(0, "batch_id", request.batch_id)
        # 追加预测结果列
        df_log["attack_type"] = [p["attack_type"] for p in predictions]
        df_log["confidence"] = [p["confidence"] for p in predictions]

        db_service.insert_batch(df_log)

    except Exception as e:
        # DuckDB 写入失败不阻断响应，记录日志后继续返回推理结果
        # 原因：推理结果对实时展示链路更关键，存储失败不应影响业务响应
        logger.error("DuckDB 写入失败（推理结果仍正常返回）: %s", e)

    # --- Step 3.5: 异步广播 WebSocket 告警（不阻塞当前 HTTP 响应） ---
    # 使用 create_task 将广播投入事件循环后立即返回，HTTP 响应无需等待
    asyncio.create_task(_broadcast_realtime_update(request.timestamp, predictions, request.records))

    # --- Step 4: 组装响应 ---
    results = [
        PredictResultItem(
            ip=request.records[i].source_ip,
            attack_type=predictions[i]["attack_type"],
            confidence=predictions[i]["confidence"],
        )
        for i in range(len(request.records))
    ]

    return BatchPredictResponse(batch_id=request.batch_id, results=results)


# =============================================================================
# WebSocket 广播辅助协程
# 由 asyncio.create_task 在事件循环中异步执行，不阻塞 HTTP 响应
# =============================================================================

async def _broadcast_realtime_update(
    timestamp: int,
    predictions: list[dict],
    records: list,
) -> None:
    """
    构造并广播单批次实时告警包。

    推送包结构：
    {
        "type": "realtime_update",
        "timestamp": <int>,
        "batch_stats": { "total": N, "Normal": n, "DoS": n, "BruteForce": n },
        "alerts": [  // 仅非 Normal 的高危条目，最多 5 条
            { "ip": "...", "attack_type": "DoS", "confidence": 0.98 }
        ]
    }

    "正常流量"类型名从 ATTACK_LABEL_MAP[0] 动态读取，禁止硬编码。
    """
    try:
        # --- 动态构建批次统计，键从 ATTACK_LABEL_MAP 读取 ---
        normal_label = ATTACK_LABEL_MAP[0]   # 当前为 "Normal"，未来可能变化
        batch_stats: dict = {"total": len(predictions)}
        for label_str in ATTACK_LABEL_MAP.values():
            batch_stats[label_str] = 0
        for p in predictions:
            if p["attack_type"] in batch_stats:
                batch_stats[p["attack_type"]] += 1

        # --- 提取高危告警（非 Normal 类型），限制最多 5 条防止拥塞 ---
        alerts = [
            {
                "ip": records[i].source_ip,
                "attack_type": predictions[i]["attack_type"],
                "confidence": predictions[i]["confidence"],
            }
            for i in range(len(predictions))
            if predictions[i]["attack_type"] != normal_label
        ][:5]

        payload = {
            "type": "realtime_update",
            "timestamp": timestamp,
            "batch_stats": batch_stats,
            "alerts": alerts,
        }

        await ws_manager.broadcast(payload)

    except Exception as e:
        # 广播失败只记录日志，绝不向上抛出（Task 内异常不影响主流程）
        logger.error("WebSocket 广播失败: %s", e)
