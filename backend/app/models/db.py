from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from ..config import get_settings

settings = get_settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
db_path = settings.data_dir / "rag.db"
engine = create_engine(f"sqlite:///{db_path}", echo=False, connect_args={"check_same_thread": False})


def init_db() -> None:
    from . import entities  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine, expire_on_commit=False)
