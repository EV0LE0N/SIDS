from fastapi import APIRouter, HTTPException
import json
import os

# 硬编码路径或从 config 读取
STATS_PATH = "/app/data/processed/dashboard_stats.json"

router = APIRouter(tags=["统计数据"])

@router.get("/stats")
async def get_stats():
    if not os.path.exists(STATS_PATH):
        raise HTTPException(status_code=404, detail="Stats not found")
    with open(STATS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)