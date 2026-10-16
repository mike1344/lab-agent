from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile

from app.common.exceptions import BusinessException
from app.common.response import BizCode, Response
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["文件上传"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def detect_image_suffix(content: bytes) -> str | None:
    """根据文件内容识别图片类型，不能只相信客户端声明的 MIME。

    这里检查三种格式最关键的文件头/尾标记，足以拦截把脚本或文本伪装成图片的
    常见情况。正式图片处理服务还可以再用 Pillow 解码并重新编码一次。
    """
    if (
        content.startswith(b"\x89PNG\r\n\x1a\n")
        and content[12:16] == b"IHDR"
        and b"IEND" in content[-24:]
    ):
        return ".png"
    if content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9"):
        return ".jpg"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return None


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    """上传图片并返回静态访问地址，限制类型和 5MB 大小。"""
    declared_suffix = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if not declared_suffix:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="只支持 JPG、PNG、WEBP 图片",
        )

    content = await file.read(MAX_IMAGE_SIZE + 1)
    await file.close()
    if len(content) > MAX_IMAGE_SIZE:
        raise BusinessException(code=BizCode.BAD_REQUEST, message="图片大小不能超过 5MB")

    detected_suffix = detect_image_suffix(content)
    if not detected_suffix or detected_suffix != declared_suffix:
        raise BusinessException(
            code=BizCode.BAD_REQUEST,
            message="图片内容与文件类型不匹配",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{detected_suffix}"
    (UPLOAD_DIR / filename).write_bytes(content)
    return Response.success(
        message="上传成功",
        data={"filename": filename, "url": f"/uploads/{filename}"},
    )
