from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from crud.source import *
from crud.note import *
from config import configer
from models import User
from service.auth import get_current_user
from service.database import get_session
from utils import logger
from pathlib import Path
from utils.response import success_response


router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{filename}")
async def handle_serve_file(filename: str,
                            user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_session)):

    source = await db_get_source_by_filename(db, filename)
    if source:
        owner_user_id = source.notebook.user_id
        is_public = source.notebook.is_public
        notebook_id = source.notebook.id
    else:
        note = await db_get_note_by_file_name(db, filename)
        if note:
            owner_user_id = note.notebook.user_id
            is_public = note.notebook.is_public
            notebook_id = note.notebook.id
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if is_public:
        logger.debug(f"Serving public file: {filename} from notebook: {notebook_id}")
    elif not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    elif user.id != owner_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    file_path = os.path.join(os.path.join(configer.upload_path, str(owner_user_id)), filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    extension = Path(file_path).suffix
    ext_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif":  "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".pdf": "application/pdf"
    }
    content_type = ext_map.get(extension, "application/octet-stream")
    response_data = {
        "Content-Type": content_type,
        "Cache-Control": "public, max-age=3600" if is_public else "no-cache",
        "file": os.path.abspath(file_path)
    }

    return success_response(message="识别文件信息成功", data=response_data)
