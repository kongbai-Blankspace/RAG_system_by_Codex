from __future__ import annotations

from fastapi import APIRouter, Query

from ..models.schemas import (
    ChatMessageResponse,
    ChatSession,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    CreateChatSessionRequest,
    SendChatMessageRequest,
)
from ..services import chat

router = APIRouter(prefix="/chat/sessions", tags=["Chat"])


@router.get("", response_model=ChatSessionListResponse)
def list_sessions(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return chat.list_sessions(page, page_size)


@router.post("", response_model=ChatSession, status_code=201)
def create_session(payload: CreateChatSessionRequest):
    return chat.create_session(payload)


@router.get("/{session_id}", response_model=ChatSessionDetailResponse)
def get_session(session_id: str):
    return chat.get_session_detail(session_id)


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: str):
    chat.delete_session(session_id)


@router.post("/{session_id}/messages", response_model=ChatMessageResponse)
def send_message(session_id: str, payload: SendChatMessageRequest):
    return chat.send_message(session_id, payload)
