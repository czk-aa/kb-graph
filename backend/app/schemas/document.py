from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    title: str = Field(default="未命名文档", max_length=512)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)


class DocumentContentPut(BaseModel):
    content_json: dict | None = None
    content_text: str = ""


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    space_id: int
    title: str
    source_type: str
    status: str
    summary: str | None
    tags: list | None
    content_text: str
    created_by: int
    created_at: datetime
    updated_at: datetime


class DocumentDetailOut(DocumentOut):
    content_json: dict | None = None


class DocumentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    version_no: int
    content_md: str
    created_by: int
    created_at: datetime


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    space_id: int
    document_id: int | None
    job_type: str
    status: str
    error: str | None
    created_at: datetime
    updated_at: datetime
