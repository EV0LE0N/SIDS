# backend/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import stats, predict, realtime, simulator, ws, assets
from services.model_service import load_model, get_model_status
from services.simulator_service import stop_replay
from services import db_service
import os


# =============================================================================
# 应用生命周期管理
# 使用 lifespan（FastAPI 推荐方式，替代已废弃的 on_event）
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 启动阶段 ---
    print("正在初始化系统资源...")
    load_model()
    db_service.init_db()
    print("系统启动完成。")

    yield  # 应用正常运行期间挂起在此

    # --- 关闭阶段：优雅终止所有后台任务，防止内存泄漏 ---
    print("系统正在关闭，终止回放引擎后台任务...")
    await stop_replay()
    print("系统资源已释放，关闭完成。")


app = FastAPI(
    title="网络攻击检测系统API",
    version="3.0.0",
    lifespan=lifespan,
)

# 配置CORS（内网演示系统，允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600
)

from routers import stats, predict, realtime, simulator, ws, assets, auth

# 注册路由
app.include_router(stats.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
app.include_router(realtime.router, prefix="/api")
app.include_router(simulator.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(ws.router)   # WebSocket 路由：无 /api 前缀，路径为 /ws/alerts

# 健康检查 (增强版)
@app.get("/health")
async def health_check():
    stats_path = "/app/data/processed/dashboard_stats.json"
    return {
        "status": "healthy",
        "message": "系统正常运行中",
        "model_ready": get_model_status(),   # 模型是否已成功加载
        "stats_ready": os.path.exists(stats_path)  # 仪表盘统计文件是否就绪
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)