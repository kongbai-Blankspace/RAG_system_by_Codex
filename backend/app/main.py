from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, documents, health, vector_stores
from .config import get_settings
from .models.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(name)s: %(message)s'
)

settings = get_settings()

app = FastAPI(title=settings.app_name, openapi_url="/openapi.json", docs_url=settings.docs_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(health.router)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(vector_stores.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {"message": "RAG backend running", "port": settings.port}
