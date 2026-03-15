# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import stats, predict
from services.model_service import load_model, get_model_status
import os

app = FastAPI(title="网络攻击检测系统API", version="1.0.0")

# 配置CORS（内网演示系统，允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600
)

# 注册路由
app.include_router(stats.router, prefix="/api")
app.include_router(predict.router, prefix="/api")

# --- 核心：系统启动时预加载模型到内存 ---
@app.on_event("startup")
async def startup_event():
    print("正在初始化系统资源...")
    load_model()
    print("系统启动完成。")

# 健康检查 (增强版)
@app.get("/health")
async def health_check():
    stats_path = "/app/data/processed/dashboard_stats.json"
    return {
        "status": "healthy",
        "message": "系统正常运行中",
        "model_ready": get_model_status(),  # 模型是否已成功加载
        "stats_ready": os.path.exists(stats_path)  # 仪表盘统计文件是否就绪
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)