"""NutriGenie FastAPI 应用入口"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库，关闭时清理"""
    print(f"[Startup] {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    yield
    print("[Shutdown] 应用关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Native Personalized Nutrition Planning System",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求耗时中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time-Ms"] = str(round(process_time * 1000, 1))
    return response


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"},
    )


# ─── 注册路由 ─────────────────────────────────────

from app.api.routes import admin, auth, profiles, recipes, ingredients, plans, knowledge, rag_qa

app.include_router(profiles.router, prefix="/api/v1")
app.include_router(recipes.router, prefix="/api/v1")
app.include_router(ingredients.router, prefix="/api/v1")
app.include_router(plans.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(rag_qa.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}
