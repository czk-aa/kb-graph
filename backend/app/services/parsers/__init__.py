"""按扩展名分发解析器。"""
from pathlib import Path

from app.core.exceptions import ValidationError

_PARSERS = {
    ".md": "app.services.parsers.md",
    ".markdown": "app.services.parsers.md",
    ".pdf": "app.services.parsers.pdf",
    ".docx": "app.services.parsers.docx",
}

SUPPORTED_EXTS = sorted(_PARSERS.keys())


def parse_file(path: Path) -> str:
    """按扩展名解析文件为纯文本。"""
    ext = path.suffix.lower()
    module_path = _PARSERS.get(ext)
    if module_path is None:
        raise ValidationError(f"不支持的文件类型：{ext}（支持 {'/'.join(SUPPORTED_EXTS)}）")
    import importlib

    module = importlib.import_module(module_path)
    return module.parse(path)
