from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException
from langchain.schema import HumanMessage, SystemMessage
from langchain_community.chat_models import FakeListChatModel
from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from sqlmodel import func, select

from ..config import get_settings
from ..models.db import get_session
from ..models.entities import ChatMessage as ChatMessageEntity
from ..models.entities import ChatSession as ChatSessionEntity
from ..models.schemas import (
    ChatMessage,
    ChatMessageResponse,
    ChatSession,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    CreateChatSessionRequest,
    DocumentSnippet,
    RecallRequest,
    SendChatMessageRequest,
)
from . import vector_stores

settings = get_settings()
logger = logging.getLogger(__name__)

try:
    from langchain.chat_models import init_chat_model  # type: ignore
except ImportError:  # pragma: no cover
    init_chat_model = None  # type: ignore

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    ChatOpenAI = None  # type: ignore


class GraphState(dict):
    question: str
    messages: List[Any]
    answer: Optional[str]
    context: str
    citations: List[DocumentSnippet]
    vectorStoreId: Optional[str]
    recallRequest: RecallRequest


def build_chat_model() -> BaseChatModel:
    """Initialise chat model using DeepSeek first, fall back to OpenAI or fake model."""

    prefer_deepseek = bool(settings.deepseek_api_key) or settings.openai_base_url.startswith(
        "https://api.deepseek.com"
    )
    api_key = (
        settings.deepseek_api_key
        if prefer_deepseek and settings.deepseek_api_key
        else settings.openai_api_key or settings.deepseek_api_key
    )

    if not api_key or api_key == "test-key":
        logger.warning("No chat model API key configured, using fake responses")
        return FakeListChatModel(responses=["我不知道"])

    base_url = settings.openai_base_url or None
    prefer_init = bool(base_url and base_url != "https://api.openai.com/v1")

    if prefer_init and init_chat_model is not None:
        try:
            kwargs: Dict[str, Any] = {"model": settings.model_name, "temperature": 0}
            if base_url:
                kwargs["base_url"] = base_url
            if prefer_deepseek:
                kwargs.setdefault("model_provider", "deepseek")
                kwargs.setdefault("api_key", api_key)
            model = init_chat_model(**kwargs)  # type: ignore[arg-type]
            logger.info("Initialised chat model via init_chat_model (%s)", model.__class__.__name__)
            return model
        except Exception as exc:  # pragma: no cover - logged and fallback
            logger.exception("Failed to initialise chat model via init_chat_model: %s", exc)

    if ChatOpenAI is not None:
        try:
            model = ChatOpenAI(
                model=settings.model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=0,
            )
            logger.info("Initialised ChatOpenAI model (%s)", model.__class__.__name__)
            return model
        except Exception as exc:  # pragma: no cover - logged and fallback
            logger.exception("Failed to initialise ChatOpenAI model: %s", exc)

    logger.warning("Falling back to fake chat model responses")
    return FakeListChatModel(responses=["我不知道"])


chat_model = build_chat_model()
logger.info("Chat model ready: %s", chat_model.__class__.__name__)

SYSTEM_PROMPT = (
    "你是企业知识库助手。若检索到参考片段，请结合它们回答；若未检索到参考资料，也可以依靠常识和经验回答。只有在确实无法回答时，才说‘我不知道’。"
)


def _build_graph():
    workflow = StateGraph(GraphState)

    def ingest(state: GraphState) -> GraphState:
        store_id = state.get("vectorStoreId")
        citations: List[DocumentSnippet] = []
        context = ""
        if store_id:
            recall_resp = vector_stores.recall(store_id, state["recallRequest"])
            citations = recall_resp.items
            context = "\n\n".join(item.content for item in citations)
        state["citations"] = citations
        state["context"] = context
        return state

    def respond(state: GraphState) -> Dict[str, Any]:
        context = state.get("context", "")
        question = state["question"]
        citations = state.get("citations", [])
        debug_parts: List[str] = [
            f"model={chat_model.__class__.__name__}",
            f"citations={len(citations)}",
            "context=present" if context else "context=missing",
        ]
        if context:
            user_prompt = "".join(
                [
                    f"问题：{question}\n\n",
                    f"参考资料：\n{context}\n\n",
                    "请结合参考资料，用中文回答用户问题。如参考资料不足，可以补充常识性的说明。",
                ]
            )
        else:
            user_prompt = "".join(
                [
                    f"用户问题：{question}\n",
                    "没有检索到参考资料，请依靠通用知识以中文回答用户，注意保持礼貌和准确。",
                ]
            )
        try:
            response = chat_model.invoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt),
                ]
            )
            content = getattr(response, "content", response) or "我不知道"
            debug_parts.append("invoke=success")
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("Chat model invocation failed: %s", exc)
            content = "调用大模型失败，请检查模型名称、密钥或代理配置。"
            debug_parts.append(f"invoke=error:{exc}")
        else:
            logger.info("Chat answer generated | question=%s | citations=%s", question, len(citations))
            if content.strip() in {"我不知道", "不知道"}:
                debug_parts.append("answer=unknown")
                if context:
                    content = "抱歉，根据当前知识库片段仍无法回答。请尝试换个问法或补充文档。"
                else:
                    content = "你好！目前没有检索到知识库内容。我可以先回答一些通用问题，或者你也可以上传文档后再试。"
            else:
                debug_parts.append("answer=ok")
        debug_line = "[debug " + " | ".join(debug_parts) + "]"
        logger.debug("Chat respond stats %s", debug_line)
        answer_text = content
        state["answer"] = answer_text
        state["citations"] = citations
        return state

    workflow.add_node("ingest", ingest)
    workflow.add_node("respond", respond)
    workflow.add_edge(START, "ingest")
    workflow.add_edge("ingest", "respond")
    workflow.add_edge("respond", END)
    return workflow.compile()


rag_executor = _build_graph()


def _map_session(entity: ChatSessionEntity) -> ChatSession:
    return ChatSession(
        id=entity.session_id,
        title=entity.title,
        createdAt=entity.created_at,
        updatedAt=entity.updated_at,
    )


def list_sessions(page: int, page_size: int) -> ChatSessionListResponse:
    with get_session() as session:
        total = session.exec(select(func.count(ChatSessionEntity.session_id))).one()
        items = (
            session.exec(
                select(ChatSessionEntity)
                .order_by(ChatSessionEntity.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
    mapped = [_map_session(item) for item in items]
    total = int(total or 0)
    return ChatSessionListResponse(items=mapped, page=page, pageSize=page_size, total=total)


def create_session(payload: CreateChatSessionRequest) -> ChatSession:
    entity = ChatSessionEntity(session_id=uuid4().hex, title=payload.title or "新的对话")
    with get_session() as session:
        session.add(entity)
        session.commit()
        session.refresh(entity)
    return _map_session(entity)


def delete_session(session_id: str) -> None:
    with get_session() as session:
        entity = session.exec(select(ChatSessionEntity).where(ChatSessionEntity.session_id == session_id)).first()
        if not entity:
            raise HTTPException(status_code=404, detail="Session not found")
        messages = session.exec(select(ChatMessageEntity).where(ChatMessageEntity.session_id == session_id)).all()
        for msg in messages:
            session.delete(msg)
        session.delete(entity)
        session.commit()


def get_session_detail(session_id: str) -> ChatSessionDetailResponse:
    with get_session() as session:
        entity = session.exec(select(ChatSessionEntity).where(ChatSessionEntity.session_id == session_id)).first()
        if not entity:
            raise HTTPException(status_code=404, detail="Session not found")
        message_entities = session.exec(
            select(ChatMessageEntity)
            .where(ChatMessageEntity.session_id == session_id)
            .order_by(ChatMessageEntity.timestamp)
        ).all()
    messages = [
        ChatMessage(
            id=m.message_id,
            role=m.role,
            content=m.content,
            timestamp=m.timestamp,
            citations=[DocumentSnippet(**c) for c in m.citations],
        )
        for m in message_entities
    ]
    return ChatSessionDetailResponse(session=_map_session(entity), messages=messages)


def send_message(session_id: str, payload: SendChatMessageRequest) -> ChatMessageResponse:
    with get_session() as session:
        session_entity = session.exec(select(ChatSessionEntity).where(ChatSessionEntity.session_id == session_id)).first()
        if not session_entity:
            raise HTTPException(status_code=404, detail="Session not found")
        user_msg = ChatMessageEntity(
            message_id=uuid4().hex,
            session_id=session_id,
            role="user",
            content=payload.message,
            timestamp=datetime.utcnow(),
            citations=[],
        )
        session.add(user_msg)
        session.commit()

    recall_request = RecallRequest(query=payload.message, topK=3, withContent=True)
    result = rag_executor.invoke(
        {
            "question": payload.message,
            "messages": [HumanMessage(content=payload.message)],
            "vectorStoreId": payload.vectorStoreId,
            "recallRequest": recall_request,
            "session_id": session_id,
        }
    )
    logger.info("RAG graph output: %r", result)
    answer = result.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        logger.error("Graph output missing usable 'answer': %r", result)
        answer = "[GraphMissingAnswer] 模型没有返回内容"
    citations = result.get("citations", [])

    assistant_entity = ChatMessageEntity(
        message_id=uuid4().hex,
        session_id=session_id,
        role="assistant",
        content=answer,
        timestamp=datetime.utcnow(),
        citations=[c.model_dump() for c in citations],
    )
    with get_session() as session:
        session.add(assistant_entity)
        session.exec(select(ChatSessionEntity).where(ChatSessionEntity.session_id == session_id)).first()
        session_entity = session.get(ChatSessionEntity, session_id)
        if session_entity:
            session_entity.updated_at = datetime.utcnow()
        session.commit()

    return ChatMessageResponse(
        sessionId=session_id,
        message=ChatMessage(
            id=assistant_entity.message_id,
            role="assistant",
            content=assistant_entity.content,
            timestamp=assistant_entity.timestamp,
            citations=citations,
        ),
    )
