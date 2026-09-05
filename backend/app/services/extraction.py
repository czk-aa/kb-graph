"""实体关系抽取：prompt + JSON 校验 + 修复重试 + 规则去重合并。"""
import logging
import re
import unicodedata

from pydantic import BaseModel, Field, ValidationError as PydValidationError, field_validator

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM_PROMPT = """你是知识图谱构建专家。仅从给定文本中抽取实体与关系。

规则：
1. 只使用文本中明确出现的信息，禁止推测、禁止用外部知识补全；
2. 实体名使用文中出现的规范化短名称；type 只能取：
   person|organization|concept|technology|product|event|other；
3. 每条关系必须给出 evidence_quote：从原文逐字摘录、不超过 200 字；
4. 文本中没有可抽取内容时返回空数组；
5. 只输出一个 JSON 对象，不要任何解释或 markdown 代码块。

输出格式：
{"entities":[{"name":"...","type":"concept","description":"...","aliases":["..."]}],
 "relations":[{"source":"实体A","target":"实体B","relation":"uses","description":"...","evidence_quote":"..."}]}"""


class ExtractedEntity(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: str = Field(default="other")
    description: str = ""
    aliases: list[str] = Field(default_factory=list)

    @field_validator("type")
    @classmethod
    def check_type(cls, v: str) -> str:
        allowed = {"person", "organization", "concept", "technology", "product", "event", "other"}
        v = v.strip().lower()
        if v not in allowed:
            return "other"
        return v


class ExtractedRelation(BaseModel):
    source: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=128)
    relation: str = Field(min_length=1, max_length=64)
    description: str = ""
    evidence_quote: str = Field(default="", max_length=200)


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)


def normalize_name(name: str) -> str:
    """lower + 去首尾标点 + 压缩空白 + NFKC。"""
    s = unicodedata.normalize("NFKC", name).strip().lower()
    s = re.sub(r"[\s]+", " ", s)
    s = s.strip(" \t\r\n.,;:!?、。；：！？·'\"“”‘’（）()[]{}【】")
    return s


def parse_extraction(raw: str) -> ExtractionResult:
    """解析 LLM 原始输出 → ExtractionResult；失败抛异常由上层重试。"""
    from app.services.llm import _parse_json_loose

    data = _parse_json_loose(raw)
    return ExtractionResult.model_validate(data)


def repair_prompt(raw: str, error: str) -> str:
    return (
        f"你之前的输出无法解析为合法 JSON。\n错误：{error}\n"
        f"原输出：\n{raw[:4000]}\n\n请仅修正为合法 JSON，不要任何解释。"
    )


async def extract_from_text(text: str) -> ExtractionResult | None:
    """调用 LLM 抽取；带一次修复重试；两次失败返回 None（不阻塞整篇）。"""
    from app.services.registry import get_llm_client

    llm = get_llm_client()
    try:
        data = await llm.chat_json(EXTRACT_SYSTEM_PROMPT, text)
        return ExtractionResult.model_validate(data)
    except (PydValidationError, ValueError, KeyError) as first_error:
        logger.warning("抽取解析失败，尝试修复重试: %s", first_error)
        try:
            raw = await llm.chat_json(
                EXTRACT_SYSTEM_PROMPT,
                text + "\n\n" + repair_prompt(str(first_error), str(first_error)),
            )
            return ExtractionResult.model_validate(raw)
        except Exception:  # noqa: BLE001
            logger.warning("抽取修复重试仍失败，跳过该 chunk")
            return None
