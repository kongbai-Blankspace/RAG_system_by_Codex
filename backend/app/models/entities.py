from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class DocumentTask(SQLModel, table=True):
    task_id: str = Field(primary_key=True, index=True)
    file_name: str
    file_type: str
    file_size: int
    status: str = Field(default="pending", index=True)
    validation: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    file_path: str


class VectorStoreRecord(SQLModel, table=True):
    store_id: str = Field(primary_key=True, index=True)
    name: str
    document_task_id: str = Field(index=True)
    config: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    status: str = Field(default="building", index=True)
    failure_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VectorStoreTask(SQLModel, table=True):
    task_id: str = Field(primary_key=True)
    store_id: str = Field(index=True)
    status: str = Field(default="queued")
    progress: float = Field(default=0.0)
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatSession(SQLModel, table=True):
    session_id: str = Field(primary_key=True, index=True)
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(SQLModel, table=True):
    message_id: str = Field(primary_key=True)
    session_id: str = Field(index=True)
    role: str = Field(index=True)
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    citations: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))

