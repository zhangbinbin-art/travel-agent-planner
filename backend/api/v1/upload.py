"""本地图片上传接口。

图片落盘到 backend/static/uploads/<YYYYMM>/<uuid>.<ext>，
再通过 /static 静态目录对外提供访问，返回绝对 URL 供前端直接回填。
"""

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from api.deps import get_current_user
from models import User

router = APIRouter()

# backend/static/uploads
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "static" / "uploads"
MAX_SIZE = 5 * 1024 * 1024  # 5MB
CHUNK_SIZE = 256 * 1024

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


@router.post("/image")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 jpg/png/webp 格式的图片")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS:
        ext = ALLOWED_TYPES[content_type]

    sub_dir = datetime.now().strftime("%Y%m")
    target_dir = UPLOAD_ROOT / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    target = target_dir / filename

    size = 0
    try:
        with target.open("wb") as out:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_SIZE:
                    raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")
                out.write(chunk)
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    except Exception:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="图片保存失败")
    finally:
        await file.close()

    if size == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="图片内容为空")

    path = f"/static/uploads/{sub_dir}/{filename}"
    return {
        "url": str(request.base_url).rstrip("/") + path,
        "path": path,
        "filename": filename,
        "size": size,
    }
