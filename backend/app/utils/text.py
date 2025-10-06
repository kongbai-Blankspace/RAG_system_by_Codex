from __future__ import annotations

from pathlib import Path
from typing import Optional


def _extract_pdf_with_pypdf(path: Path) -> Optional[str]:
    try:
        from PyPDF2 import PdfReader
        from PyPDF2.errors import PdfReadError
    except ImportError:
        return None

    try:
        reader = PdfReader(path)
    except Exception:
        return None

    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception:
            return None

    text_parts: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except PdfReadError:
            return None
        except Exception:
            text = ""
        text_parts.append(text)
    combined = "\n".join(text_parts).strip()
    return combined or None


def _extract_pdf_with_pdfminer(path: Path) -> Optional[str]:
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
    except ImportError:
        return None

    try:
        text = pdfminer_extract(str(path))
    except Exception:
        return None
    return text.strip() or None


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        for extractor in (_extract_pdf_with_pypdf, _extract_pdf_with_pdfminer):
            text = extractor(path)
            if text:
                return text
        raise RuntimeError("无法解析 PDF 文档内容，请确认文件未加密且内容可复制")
    raise ValueError(f"Unsupported extension: {ext}")
