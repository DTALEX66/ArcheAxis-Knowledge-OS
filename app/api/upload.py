"""
File upload API for multi-format document import
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import hashlib
from pathlib import Path

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])


UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "pdf": ["application/pdf"],
    "epub": ["application/epub+zip"],
    "audio": ["audio/mpeg", "audio/wav", "audio/ogg", "audio/m4a"],
    "video": ["video/mp4", "video/webm", "video/ogg"],
    "text": ["text/plain", "text/markdown"],
}


def get_file_hash(content: bytes) -> str:
    """计算文件SHA256哈希"""
    return hashlib.sha256(content).hexdigest()


@router.post("/document")
async def upload_document(file: UploadFile = File(...)):
    """
    上传文档文件（PDF、EPUB、文本）
    """
    try:
        # 读取文件内容
        content = await file.read()

        # 验证文件类型
        if not file.content_type:
            raise HTTPException(status_code=400, detail="无法识别文件类型")

        # 检查是否为允许的类型
        allowed = False
        file_category = None
        for category, types in ALLOWED_EXTENSIONS.items():
            if file.content_type in types:
                allowed = True
                file_category = category
                break

        if not allowed:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file.content_type}"
            )

        # 计算文件哈希
        file_hash = get_file_hash(content)

        # 保存文件
        file_ext = Path(file.filename).suffix if file.filename else ""
        saved_path = UPLOAD_DIR / f"{file_hash}{file_ext}"

        # 避免重复上传
        if not saved_path.exists():
            with open(saved_path, "wb") as f:
                f.write(content)

        return {
            "success": True,
            "file_id": file_hash,
            "filename": file.filename,
            "size": len(content),
            "type": file_category,
            "content_type": file.content_type,
            "path": str(saved_path),
            "message": "文件上传成功"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"文件上传失败: {str(e)}"
        )


@router.post("/media")
async def upload_media(file: UploadFile = File(...)):
    """
    上传媒体文件（音频、视频）
    """
    try:
        content = await file.read()

        # 验证媒体类型
        if not file.content_type:
            raise HTTPException(status_code=400, detail="无法识别文件类型")

        is_audio = any(file.content_type in types for types in [ALLOWED_EXTENSIONS["audio"]])
        is_video = any(file.content_type in types for types in [ALLOWED_EXTENSIONS["video"]])

        if not (is_audio or is_video):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的媒体类型: {file.content_type}"
            )

        file_hash = get_file_hash(content)
        file_ext = Path(file.filename).suffix if file.filename else ""
        saved_path = UPLOAD_DIR / f"{file_hash}{file_ext}"

        if not saved_path.exists():
            with open(saved_path, "wb") as f:
                f.write(content)

        return {
            "success": True,
            "file_id": file_hash,
            "filename": file.filename,
            "size": len(content),
            "type": "audio" if is_audio else "video",
            "content_type": file.content_type,
            "path": str(saved_path),
            "message": "媒体文件上传成功"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"媒体上传失败: {str(e)}"
        )


@router.post("/batch")
async def upload_batch(files: List[UploadFile] = File(...)):
    """
    批量上传文件
    """
    results = []

    for file in files:
        try:
            content = await file.read()
            file_hash = get_file_hash(content)
            file_ext = Path(file.filename).suffix if file.filename else ""
            saved_path = UPLOAD_DIR / f"{file_hash}{file_ext}"

            if not saved_path.exists():
                with open(saved_path, "wb") as f:
                    f.write(content)

            results.append({
                "success": True,
                "filename": file.filename,
                "file_id": file_hash,
                "size": len(content)
            })
        except Exception as e:
            results.append({
                "success": False,
                "filename": file.filename,
                "error": str(e)
            })

    return {
        "total": len(files),
        "succeeded": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


@router.get("/status/{file_id}")
async def get_upload_status(file_id: str):
    """
    检查文件是否已上传
    """
    # 查找文件
    matching_files = list(UPLOAD_DIR.glob(f"{file_id}*"))

    if matching_files:
        file_path = matching_files[0]
        return {
            "exists": True,
            "file_id": file_id,
            "path": str(file_path),
            "size": file_path.stat().st_size
        }
    else:
        return {
            "exists": False,
            "file_id": file_id
        }
