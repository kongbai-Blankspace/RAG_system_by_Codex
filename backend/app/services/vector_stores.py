from __future__ import annotations

from datetime import datetime
import logging
from typing import List
from uuid import uuid4

from fastapi import HTTPException
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlmodel import select

from ..config import get_settings
from ..models.db import get_session
from ..models.entities import DocumentTask, VectorStoreRecord
from ..models.schemas import DocumentSnippet, RecallRequest, RecallResponse, VectorStoreConfig
from ..storage.vector_storage import load_vector_store, save_vector_store
from .documents import get_document_text

settings = get_settings()
logger = logging.getLogger(__name__)


class FallbackEmbeddings(Embeddings):
    """Deterministic embeddings when real embedding services are unavailable."""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:  # type: ignore[override]
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:  # type: ignore[override]
        return [float(len(text) % 97), float(hash(text) % 101), float(len(text.split()))]


def _resolve_embed_base_url() -> str:
    if settings.embed_base_url:
        return settings.embed_base_url
    if settings.openai_base_url and settings.openai_base_url != "https://api.deepseek.com/v1":
        return settings.openai_base_url
    return "https://api.openai.com/v1"


def build_embeddings() -> Embeddings:
    try:
        from langchain_openai import OpenAIEmbeddings

        api_key = settings.embed_api_key or settings.openai_api_key or settings.deepseek_api_key
        if not api_key or api_key == "test-key":
            raise ValueError("missing api key")

        base_url = _resolve_embed_base_url()
        logger.info("Using embedding backend %s", base_url)
        return OpenAIEmbeddings(
            api_key=api_key,
            base_url=base_url,
            model=settings.embed_model,
        )
    except Exception as exc:
        logger.warning("Falling back to deterministic embeddings: %s", exc)
        return FallbackEmbeddings()


_embeddings = build_embeddings()


def create_vector_store(document_task_id: str, config: VectorStoreConfig) -> VectorStoreRecord:
    with get_session() as session:
        task = session.exec(select(DocumentTask).where(DocumentTask.task_id == document_task_id)).first()
        if not task:
            raise HTTPException(status_code=404, detail="Document task not found")
        if task.status != "success":
            raise HTTPException(status_code=400, detail="文档尚未通过校验")

        text = get_document_text(task)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunkSize,
            chunk_overlap=config.overlap,
        )
        documents = splitter.create_documents([text])

        backend = "default"
        store_id = uuid4().hex
        try:
            faiss_store = FAISS.from_documents(documents, _embeddings)
        except Exception as exc:
            logger.warning("Embedding model failed (%s), falling back to deterministic embeddings", exc)
            backend = "fallback"
            fallback = FallbackEmbeddings()
            faiss_store = FAISS.from_documents(documents, fallback)
        save_vector_store(faiss_store, store_id)

        record = VectorStoreRecord(
            store_id=store_id,
            name=config.name,
            document_task_id=document_task_id,
            config={**config.dict(), "embeddingBackend": backend},
            status="ready",
            failure_reason=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


def get_vector_store(store_id: str) -> VectorStoreRecord:
    with get_session() as session:
        record = session.exec(select(VectorStoreRecord).where(VectorStoreRecord.store_id == store_id)).first()
        if not record:
            raise HTTPException(status_code=404, detail="Vector store not found")
        return record


def list_vector_stores() -> List[VectorStoreRecord]:
    with get_session() as session:
        return list(session.exec(select(VectorStoreRecord)))


def recall(store_id: str, payload: RecallRequest) -> RecallResponse:
    record = get_vector_store(store_id)
    backend = record.config.get("embeddingBackend", "default")

    embedding = FallbackEmbeddings() if backend == "fallback" else _embeddings
    store = load_vector_store(store_id, embedding)
    if not store:
        raise HTTPException(status_code=404, detail="Vector store not ready")

    try:
        retriever = store.as_retriever(search_kwargs={"k": payload.topK})
        docs = retriever.get_relevant_documents(payload.query)
    except Exception as exc:
        if backend != "fallback":
            logger.warning("Vector recall failed (%s), retrying with deterministic embeddings", exc)
            fallback_store = load_vector_store(store_id, FallbackEmbeddings())
            if not fallback_store:
                raise HTTPException(status_code=500, detail="Vector store fallback failed") from exc
            retriever = fallback_store.as_retriever(search_kwargs={"k": payload.topK})
            docs = retriever.get_relevant_documents(payload.query)
        else:
            raise

    items: List[DocumentSnippet] = []
    for idx, doc in enumerate(docs, start=1):
        metadata = {**doc.metadata}
        items.append(
            DocumentSnippet(
                id=f"{store_id}-{idx}",
                title=metadata.get("source", record.name),
                similarity=float(doc.metadata.get("score", 0.0)),
                content=doc.page_content if payload.withContent else doc.page_content[:100],
                metadata=metadata,
            )
        )
    return RecallResponse(storeId=store_id, items=items)
