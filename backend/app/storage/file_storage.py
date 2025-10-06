from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import UploadFile

from ..config import get_settings

settings = get_settings()


def save_upload_file(upload_file: UploadFile, task_id: str) -> Path:
    extension = Path(upload_file.filename or "").suffix
    target = settings.document_dir / f"{task_id}{extension}"
    with target.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    upload_file.file.seek(0)
    return target


def read_file_bytes(path: Path) -> bytes:
    return path.read_bytes()
