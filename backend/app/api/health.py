from fastapi import APIRouter

from ..config import get_settings

router = APIRouter()


@router.get("/healthz")
def healthz():
    settings = get_settings()
    return {"status": "ok", "service": settings.app_name}
