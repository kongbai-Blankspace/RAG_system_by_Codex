from __future__ import annotations

from fastapi import APIRouter

from ..models.schemas import (
    CreateVectorStoreRequest,
    CreateVectorStoreResponse,
    RecallRequest,
    RecallResponse,
    VectorStore,
    VectorStoreConfig,
    VectorStoreTaskStatusResponse,
)
from ..services import vector_stores

router = APIRouter(prefix="/vector-stores", tags=["VectorStores"])


@router.post("", response_model=CreateVectorStoreResponse, status_code=202)
def create_vector_store(payload: CreateVectorStoreRequest):
    record = vector_stores.create_vector_store(payload.documentTaskId, payload.config)
    return CreateVectorStoreResponse(
        storeId=record.store_id,
        taskId=record.store_id,
        statusUrl=f"/api/v1/vector-stores/{record.store_id}",
    )


@router.get("/{store_id}", response_model=VectorStore)
def get_vector_store(store_id: str):
    record = vector_stores.get_vector_store(store_id)
    return VectorStore(
        id=record.store_id,
        name=record.name,
        status=record.status,
        documentTaskId=record.document_task_id,
        config=VectorStoreConfig(**record.config),
        createdAt=record.created_at,
        updatedAt=record.updated_at,
        failureReason=record.failure_reason,
    )


@router.get("/{store_id}/tasks/{task_id}", response_model=VectorStoreTaskStatusResponse)
def get_vector_store_task(store_id: str, task_id: str):
    record = vector_stores.get_vector_store(store_id)
    progress = 1.0 if record.status == "ready" else 0.5
    return VectorStoreTaskStatusResponse(
        taskId=task_id,
        status=record.status,
        progress=progress,
        message=record.failure_reason,
    )


@router.post("/{store_id}/recall", response_model=RecallResponse)
def recall(store_id: str, payload: RecallRequest):
    return vector_stores.recall(store_id, payload)
