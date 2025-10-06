from __future__ import annotations

from pathlib import Path
from typing import Optional

from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

from ..config import get_settings

settings = get_settings()


def get_vector_store_path(store_id: str) -> Path:
    return settings.vector_dir / store_id


def save_vector_store(store: FAISS, store_id: str) -> None:
    path = get_vector_store_path(store_id)
    path.mkdir(parents=True, exist_ok=True)
    store.save_local(str(path))


def load_vector_store(store_id: str, embeddings: Embeddings) -> Optional[FAISS]:
    path = get_vector_store_path(store_id)
    if not path.exists():
        return None
    return FAISS.load_local(str(path), embeddings, allow_dangerous_deserialization=True)
