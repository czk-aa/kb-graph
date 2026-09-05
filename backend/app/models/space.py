import enum

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SpaceRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


ROLE_ORDER: dict[str, int] = {"member": 0, "admin": 1, "owner": 2}


class Space(Base, TimestampMixin):
    __tablename__ = "spaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(default="")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    members: Mapped[list["SpaceMember"]] = relationship(
        back_populates="space", cascade="all, delete-orphan"
    )


class SpaceMember(Base, TimestampMixin):
    __tablename__ = "space_members"
    __table_args__ = (UniqueConstraint("space_id", "user_id", name="uq_space_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[SpaceRole] = mapped_column(
        Enum(SpaceRole, native_enum=False, length=16), default=SpaceRole.member
    )

    space: Mapped[Space] = relationship(back_populates="members")
