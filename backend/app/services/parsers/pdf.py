"""PDF 文本提取（pymupdf）。"""
from pathlib import Path

import fitz


def parse(path: Path) -> str:
    parts: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            parts.append(page.get_text("text"))
    return "\n\n".join(parts).strip()
