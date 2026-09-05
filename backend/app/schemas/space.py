from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SpaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = ""


class SpaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None


class SpaceMemberAdd(BaseModel):
    email: str
    role: str = Field(default="member", pattern="^(member|admin)$")


class SpaceMemberUpdate(BaseModel):
    role: str = Field(pattern="^(member|admin)$")


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nickname: str
    avatar_url: str | None = None


class SpaceMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserBrief
    role: str
    created_at: datetime


class SpaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    owner_id: int
    created_at: datetime
    updated_at: datetime
    my_role: str = "member"
