"""RAG：prompt 组装与 SSE 生成器。"""
import json
from collections.abc import AsyncIterator
from dataclasses import asdict

from app.core.config import get_settings
from app.services.registry import get_embedding_client, get_llm_client
from app.services.retrieval import RetrievalResult, retrieve

SYSTEM_PROMPT = """你是企业知识库助手。严格依据提供的知识库上下文回答问题。

规则：
1. 使用与提问相同的语言回答；
2. 引用信息时在句末标注来源编号，如 [1]、[2]，编号对应上下文条目；
3. 上下文不足以回答时，明确说明"知识库中没有找到相关信息"，不要编造；
4. 回答简洁、结构清晰。"""


def _build_context(result: RetrievalResult) -> str:
    parts = []
    for i, hit in enumerate(result.hits, start=1):
        loc = f"{hit.document_title}"
        if hit.section_path:
            loc += f" > {hit.section_path}"
        parts.append(f"[{i}] （{loc}）\n{hit.content}")
    return "\n\n".join(parts)


def _citations(result: RetrievalResult) -> list[dict]:
    return [
        {
            "doc_id": h.document_id,
            "doc_title": h.document_title,
            "chunk_id": h.chunk_id,
            "seq": h.seq,
            "section_path": h.section_path,
            "quote": h.content[:200],
            "score": round(h.score, 4),
        }
        for h in result.hits
    ]


async def answer_stream(session_history: list[dict], question: str, space_id: int) -> AsyncIterator[dict]:
    """SSE 事件流：citations → delta* → done。

    事件格式：{"type": "citations"|"delta"|"done", ...}
    """
    settings = get_settings()

    embedder = get_embedding_client()
    query_vec = await embedder.embed_query(question)
    result = await retrieve(space_id, question, query_vec, context_k=settings.retrieve_context_k)

    yield {"type": "citations", "data": _citations(result)}

    context = _build_context(result)
    if not context:
        yield {"type": "delta", "data": {"text": "知识库中没有找到相关信息，请先上传或编写相关文档。"}}
        yield {"type": "done", "data": {"citations": [], "meta": {"vector_hits": 0}}}
        return

    user_prompt = f"知识库上下文：\n\n{context}\n\n问题：{question}"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *session_history]
    messages.append({"role": "user", "content": user_prompt})

    llm = get_llm_client()
    answer_parts: list[str] = []
    try:
        async for delta in llm.chat_stream(messages, temperature=0.3):
            answer_parts.append(delta)
            yield {"type": "delta", "data": {"text": delta}}
    except asyncio.CancelledError:  # noqa: F821
        raise

    meta = {
        "vector_hits": len(result.hits),
        "elapsed_ms": result.elapsed_ms,
        "expanded_entities": result.expanded_entities,
    }
    yield {
        "type": "done",
        "data": {"citations": _citations(result), "answer": "".join(answer_parts), "meta": meta},
    }


def sse_format(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
