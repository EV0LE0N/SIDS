from fastapi import APIRouter, HTTPException
import json
import os

STATS_PATH = "/app/data/processed/dashboard_stats.json"
CONFUSION_MATRIX_PATH = "/app/data/models/confusion_matrix.json"
EDA_SAMPLE_PATH = "/app/data/models/eda_sample.json"
FEATURE_IMPORTANCE_PATH = "/app/data/models/feature_importance.json"

router = APIRouter(tags=["统计数据"])

@router.get("/stats")
async def get_stats():
    result = {}
    
    if os.path.exists(STATS_PATH):
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            result.update(json.load(f))
    
    if os.path.exists(CONFUSION_MATRIX_PATH):
        with open(CONFUSION_MATRIX_PATH, "r", encoding="utf-8") as f:
            result["confusion_matrix"] = json.load(f)
    
    if os.path.exists(EDA_SAMPLE_PATH):
        with open(EDA_SAMPLE_PATH, "r", encoding="utf-8") as f:
            result["eda_sample"] = json.load(f)
    
    if os.path.exists(FEATURE_IMPORTANCE_PATH):
        with open(FEATURE_IMPORTANCE_PATH, "r", encoding="utf-8") as f:
            result["feature_importance"] = json.load(f)
    
    return result