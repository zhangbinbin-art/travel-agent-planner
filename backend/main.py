from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1 import health, user
from core.config import settings

app = FastAPI(title="个性化旅行规划平台API", version="0.1.0", description="基于Python的个性化旅行规划平台后端")

# 修改跨域，调试阶段放开全部源，避免localhost/127.0.0.1端口混用导致跨域拦截
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(user.router, prefix="/api/v1/user", tags=["user"])

@app.get("/")
def root():
    return {"message": "travel-bishe-backend", "docs": "/docs"}
