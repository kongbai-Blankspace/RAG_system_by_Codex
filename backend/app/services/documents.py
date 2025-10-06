from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4

from fastapi import HTTPException, UploadFile, Response
from sqlmodel import select

from ..config import get_settings
from ..models.db import get_session
from ..models.entities import DocumentTask
from ..models.schemas import DocumentTaskStatusResponse, DocumentValidation, ValidationRule
from ..storage.file_storage import save_upload_file
from ..utils.text import extract_text

settings = get_settings()


def _validate_file(upload_file: UploadFile) -> Tuple[List[ValidationRule], int]:
    rules: List[ValidationRule] = []
    filename = upload_file.filename or ""
    extension = Path(filename).suffix.lower()
    allowed = extension in settings.allowed_extensions
    rules.append(ValidationRule(rule="extension", passed=allowed, detail=f"allowed: {settings.allowed_extensions}"))

    upload_file.file.seek(0, 2)
    size = upload_file.file.tell()
    upload_file.file.seek(0)
    size_ok = size <= settings.max_file_size_mb * 1024 * 1024
    rules.append(ValidationRule(rule="size", passed=size_ok, detail=f"<= {settings.max_file_size_mb}MB"))

    if allowed and size_ok:
        temp_path = settings.document_dir / f"_tmp_{uuid4()}{extension}"
        try:
            with temp_path.open("wb") as f:
                f.write(upload_file.file.read())
            upload_file.file.seek(0)
            try:
                text = extract_text(temp_path)
            except Exception as exc:
                rules.append(
                    ValidationRule(
                        rule="content_parse",
                        passed=False,
                        detail=str(exc),
                    )
                )
                content_ok = False
            else:
                content_ok = len(text.strip()) >= settings.min_document_length
                rules.append(
                    ValidationRule(
                        rule="content_length",
                        passed=content_ok,
                        detail=f">= {settings.min_document_length} characters",
                    )
                )
        finally:
            if temp_path.exists():
                temp_path.unlink()
            upload_file.file.seek(0)
    else:
        rules.append(
            ValidationRule(
                rule="content_length",
                passed=False,
                detail="skipped due to previous failure",
            )
        )
    return rules, size


def create_document_task(upload_file: UploadFile) -> DocumentTaskStatusResponse:
    filename = upload_file.filename or "uploaded"
    rules, size = _validate_file(upload_file)
    passed = all(rule.passed for rule in rules)

    task_id = uuid4().hex
    file_path_str = ""
    if passed:
        saved_path = save_upload_file(upload_file, task_id)
        file_path_str = str(saved_path)
    else:
        upload_file.file.seek(0)

    with get_session() as session:
        task = DocumentTask(
            task_id=task_id,
            file_name=filename,
            file_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
            file_size=size,
            status="success" if passed else "failed",
            validation={"passed": passed, "rules": [rule.dict() for rule in rules]},
            message=None if passed else "文档校验未通过",
            file_path=file_path_str,
        )
        session.add(task)
        session.commit()
        session.refresh(task)

    if not passed:
        error = {
            "code": "DATASET_INVALID",
            "message": "文档校验未通过",
            "issues": [rule.dict() for rule in rules],
        }
        raise HTTPException(status_code=400, detail=error)

    return map_task_to_schema(task)


def map_task_to_schema(task: DocumentTask) -> DocumentTaskStatusResponse:
    validation = DocumentValidation(
        passed=bool(task.validation.get("passed")),
        rules=[ValidationRule(**rule) for rule in task.validation.get("rules", [])],
    )
    return DocumentTaskStatusResponse(
        taskId=task.task_id,
        status=task.status,
        fileName=task.file_name,
        fileType=task.file_type,
        fileSize=task.file_size,
        validation=validation,
        message=task.message,
        createdAt=task.created_at,
        updatedAt=task.updated_at,
    )


def get_document_task(task_id: str) -> DocumentTaskStatusResponse:
    with get_session() as session:
        task = session.exec(select(DocumentTask).where(DocumentTask.task_id == task_id)).first()
        if not task:
            raise HTTPException(status_code=404, detail="Document task not found")
        return map_task_to_schema(task)


def get_document_text(task: DocumentTask) -> str:
    if not task.file_path:
        raise HTTPException(status_code=400, detail="Document not available")
    path = Path(task.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Document file missing")
    return extract_text(path)




