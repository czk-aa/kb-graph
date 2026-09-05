"""Markdown 感知递归分块器。

策略：
1. 按标题层级切 section，记录 section_path（如 "部署 > Docker"）；
2. section 内按段落聚合到 chunk_size_tokens，带 overlap 回看；
3. 超长段落按句子/字符硬切。
"""
import re

from app.core.config import get_settings

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def count_tokens(text: str) -> int:
    """启发式：CJK 字符每字 1 token，连续非 CJK 按空格词计。"""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    rest = re.sub(r"[\u4e00-\u9fff]", " ", text)
    return cjk + len(rest.split())


def _split_long_paragraph(text: str, max_tokens: int) -> list[str]:
    """句子优先，字符兜底。"""
    sentences = re.split(r"(?<=[。！？.!?])\s*", text)
    parts: list[str] = []
    buf = ""
    for s in sentences:
        if count_tokens(buf + s) <= max_tokens:
            buf += s
            continue
        if buf:
            parts.append(buf)
        if count_tokens(s) <= max_tokens:
            buf = s
        else:
            # 字符硬切
            step = max_tokens * 2  # CJK 1 token ≈ 1 char；英文近似放大
            for i in range(0, len(s), step):
                parts.append(s[i : i + step])
            buf = ""
    if buf:
        parts.append(buf)
    return parts


def chunk_text(text: str) -> list[dict]:
    """返回 [{content, section_path, seq}]。"""
    settings = get_settings()
    size = settings.chunk_size_tokens
    overlap = settings.chunk_overlap_tokens

    # 解析标题结构
    sections: list[tuple[list[str], str]] = []  # (heading_path, body)
    path: list[str] = []
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        sections.append(([], text))
    else:
        # 首个标题前的内容
        pre = text[: matches[0].start()].strip()
        if pre:
            sections.append(([], pre))
        for i, m in enumerate(matches):
            level = len(m.group(1))
            title = m.group(2).strip()
            path = path[: level - 1] + [title]
            body_start = m.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections.append((list(path), text[body_start:body_end].strip()))

    chunks: list[dict] = []
    for heading_path, body in sections:
        if not body.strip():
            continue
        section_path = " > ".join(heading_path) if heading_path else ""
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        expanded: list[str] = []
        for p in paragraphs:
            if count_tokens(p) > size:
                expanded.extend(_split_long_paragraph(p, size))
            else:
                expanded.append(p)

        buf = ""
        for para in expanded:
            candidate = f"{buf}\n\n{para}" if buf else para
            if count_tokens(candidate) <= size:
                buf = candidate
                continue
            if buf:
                chunks.append({"content": buf, "section_path": section_path})
            # overlap：取 buf 尾部
            tail = ""
            if overlap > 0:
                tail = buf
                while tail and count_tokens(tail) > overlap:
                    tail = re.sub(r"^\S+\s*", "", tail)
            buf = f"{tail}\n\n{para}" if tail else para
        if buf.strip():
            chunks.append({"content": buf, "section_path": section_path})

    for i, c in enumerate(chunks):
        c["seq"] = i
    return chunks
