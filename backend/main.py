import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.v1 import health, user, spot, favorite, post, comment, trip, admin, merchant, hotel, upload

app = FastAPI(title="个性化旅行规划平台API", version="0.1.0", description="基于Python的个性化旅行规划平台后端")

# 本地图片上传目录（/static/uploads/...）
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(os.path.join(STATIC_DIR, "uploads"), exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

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
app.include_router(spot.router, prefix="/api/v1/spot", tags=["spot"])
app.include_router(favorite.router, prefix="/api/v1/favorite", tags=["favorite"])
app.include_router(post.router, prefix="/api/v1/post", tags=["post"])
app.include_router(comment.router, prefix="/api/v1/comment", tags=["comment"])
app.include_router(trip.router, prefix="/api/v1/trip", tags=["trip"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(merchant.router, prefix="/api/v1/merchant", tags=["merchant"])
app.include_router(hotel.router, prefix="/api/v1/hotel", tags=["hotel"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["upload"])


@app.get("/")
def root():
    return {"message": "travel-bishe-backend", "docs": "/docs"}
