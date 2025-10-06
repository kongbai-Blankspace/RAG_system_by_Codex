from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ValidationRule(BaseModel):
    rule: str
    passed: bool
    detail: Optional[str] = None


class DocumentValidation(BaseModel):
    passed: bool
    rules: List[ValidationRule] = Field(default_factory=list)


class UploadDocumentResponse(BaseModel):
    taskId: str
    statusUrl: str


class DataValidationError(BaseModel):
    code: str = Field(example="DATASET_INVALID")
    message: str
    issues: List[ValidationRule] = Field(default_factory=list)


class DocumentTaskStatusResponse(BaseModel):
    taskId: str
    status: str
    fileName: str
    fileType: str
    fileSize: int
    validation: DocumentValidation
    message: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime


class VectorStoreConfig(BaseModel):
    name: str
    chunkSize: int
    overlap: int
    topK: int


class CreateVectorStoreRequest(BaseModel):
    documentTaskId: str
    config: VectorStoreConfig


class CreateVectorStoreResponse(BaseModel):
    storeId: str
    taskId: str
    statusUrl: str


class VectorStore(BaseModel):
    id: str
    name: str
    status: str
    documentTaskId: str
    config: VectorStoreConfig
    createdAt: datetime
    updatedAt: datetime
    failureReason: Optional[str] = None


class VectorStoreTaskStatusResponse(BaseModel):
    taskId: str
    status: str
    progress: float
    message: Optional[str] = None


class DocumentSnippet(BaseModel):
    id: str
    title: str
    similarity: float
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecallRequest(BaseModel):
    query: str
    topK: int = 3
    withContent: bool = True


class RecallResponse(BaseModel):
    storeId: str
    items: List[DocumentSnippet]


class ChatSession(BaseModel):
    id: str
    title: str
    createdAt: datetime
    updatedAt: datetime


class ChatSessionListResponse(BaseModel):
    items: List[ChatSession]
    page: int
    pageSize: int
    total: int


class CreateChatSessionRequest(BaseModel):
    title: Optional[str] = None


class ChatMessage(BaseModel):
    id: str
    role: str
    content: str
    timestamp: datetime
    citations: List[DocumentSnippet] = Field(default_factory=list)


class ChatSessionDetailResponse(BaseModel):
    session: ChatSession
    messages: List[ChatMessage]


class SendChatMessageRequest(BaseModel):
    message: str
    vectorStoreId: Optional[str] = None


class ChatMessageResponse(BaseModel):
    sessionId: str
    message: ChatMessage


class ErrorResponse(BaseModel):
    code: str
    message: str
    traceId: Optional[str] = None
