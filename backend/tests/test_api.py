import io
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))


@pytest.fixture(scope="session")
def test_env(tmp_path_factory):
    tmp_root = tmp_path_factory.mktemp("backend_data")
    os.environ["DATA_DIR"] = str(tmp_root / "db")
    os.environ["DOCUMENT_DIR"] = str(tmp_root / "documents")
    os.environ["VECTOR_DIR"] = str(tmp_root / "vectors")
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")

    from app.config import get_settings
    from app.models.db import init_db

    get_settings.cache_clear()  # type: ignore[attr-defined]
    settings = get_settings()
    settings.document_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_dir.mkdir(parents=True, exist_ok=True)

    init_db()
    return settings


@pytest.fixture()
def client(test_env):
    from app.main import app

    return TestClient(app)


def _create_text_file(content: str, name: str = "doc.txt"):
    return name, content.encode("utf-8")


def test_upload_document_success(client):
    filename, data = _create_text_file("示例内容" * 50)
    files = {"file": (filename, io.BytesIO(data), "text/plain")}
    response = client.post("/api/v1/documents", files=files)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    task_id = body["taskId"]

    resp2 = client.get(f"/api/v1/documents/{task_id}")
    assert resp2.status_code == 200
    assert resp2.json()["validation"]["passed"] is True


def test_upload_document_invalid_extension(client):
    files = {"file": ("doc.exe", io.BytesIO(b"fake"), "application/octet-stream")}
    response = client.post("/api/v1/documents", files=files)
    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["code"] == "DATASET_INVALID"


def test_vector_store_and_recall_flow(client):
    filename, data = _create_text_file("LangGraph 指南" * 100)
    files = {"file": (filename, io.BytesIO(data), "text/plain")}
    upload = client.post("/api/v1/documents", files=files).json()
    task_id = upload["taskId"]

    payload = {
        "documentTaskId": task_id,
        "config": {
            "name": "测试知识库",
            "chunkSize": 256,
            "overlap": 32,
            "topK": 3
        }
    }
    store_resp = client.post("/api/v1/vector-stores", json=payload)
    assert store_resp.status_code == 202
    store_id = store_resp.json()["storeId"]

    recall_req = {"query": "LangGraph", "topK": 2, "withContent": True}
    recall_resp = client.post(f"/api/v1/vector-stores/{store_id}/recall", json=recall_req)
    assert recall_resp.status_code == 200
    items = recall_resp.json()["items"]
    assert len(items) <= 2


def test_chat_session_flow(client):
    session_resp = client.post("/api/v1/chat/sessions", json={"title": "测试对话"})
    assert session_resp.status_code == 201
    session_id = session_resp.json()["id"]

    message_resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"message": "介绍一下系统"}
    )
    assert message_resp.status_code == 200
    data = message_resp.json()
    assert data["message"]["role"] == "assistant"

    detail_resp = client.get(f"/api/v1/chat/sessions/{session_id}")
    assert detail_resp.status_code == 200
    assert len(detail_resp.json()["messages"]) >= 2
