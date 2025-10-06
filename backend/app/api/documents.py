from __future__ import annotations

from fastapi import APIRouter, UploadFile

from ..models.schemas import DocumentTaskStatusResponse
from ..services import documents

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentTaskStatusResponse, status_code=201)
async def upload_document(file: UploadFile):
    return documents.create_document_task(file)


@router.get("/{task_id}", response_model=DocumentTaskStatusResponse)
async def get_document_task(task_id: str):
    return documents.get_document_task(task_id)
