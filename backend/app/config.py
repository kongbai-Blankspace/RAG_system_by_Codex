import json
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_file() -> str | Path:
    candidates = [
        Path(__file__).resolve().parents[2] / '.env',
        Path(__file__).resolve().parents[1] / '.env',
        Path(__file__).resolve().parent / '.env',
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return '.env'


class Settings(BaseSettings):
    app_name: str = "RAG Backend"
    api_prefix: str = "/api/v1"
    docs_url: str | None = "/docs"
    port: int = Field(default=8002, description="Backend service port")

    # storage
    data_dir: Path = Path("storage")
    document_dir: Path = Path("storage/documents")
    vector_dir: Path = Path("storage/vectors")

    # upload constraints
    allowed_extensions_raw: str = Field(default=".txt,.md,.pdf", alias="ALLOWED_EXTENSIONS")
    max_file_size_mb: int = 50
    min_document_length: int = 200

    # langchain configuration
    model_name: str = Field(default="deepseek-chat")
    embed_model: str = Field(default="text-embedding-3-small")
    openai_base_url: str = Field(default="https://ai.devtool.tech/proxy/v1")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    embed_base_url: str | None = Field(default=None, alias="EMBED_BASE_URL")
    embed_api_key: str | None = Field(default=None, alias="EMBED_API_KEY")

    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def allowed_extensions(self) -> List[str]:
        raw = self.allowed_extensions_raw
        if isinstance(raw, str):
            text = raw.strip()
            if not text:
                items: List[str] = []
            elif text.startswith('[') and text.endswith(']'):
                try:
                    parsed = json.loads(text)
                    items = [str(item) for item in parsed] if isinstance(parsed, list) else [str(parsed)]
                except json.JSONDecodeError:
                    items = [part.strip() for part in text.split(',')]
            else:
                items = [part.strip() for part in text.split(',')]
        else:
            items = [str(part).strip() for part in raw]

        normalized: List[str] = []
        for item in items:
            if not item:
                continue
            if not item.startswith('.'):
                item = f'.{item}'
            normalized.append(item.lower())
        return normalized or [".txt", ".md", ".pdf"]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.document_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_dir.mkdir(parents=True, exist_ok=True)
    return settings


