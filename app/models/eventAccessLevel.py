
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class EventAccessLevel(SQLModel, table=True):
    __tablename__ = "event_access_levels"

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "code",
            name="uq_event_access_levels_event_code",
        ),
        UniqueConstraint(
            "event_id",
            "id",
            name="uq_event_access_levels_event_id_id",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)

    event_id: int = Field(
        foreign_key="events.id",
        nullable=False,
        index=True,
    )

    name: str = Field(max_length=120, nullable=False)
    code: str = Field(max_length=60, nullable=False)
    description: str | None = Field(default=None, max_length=500)
    color: str | None = Field(
        default=None,
        max_length=7,
        regex=r"^#(?:[0-9a-fA-F]{3}){1,2}$",
    )

    is_active: bool = Field(default=True, nullable=False)


class EventAccessLevelCreate(SQLModel):
    name: str = Field(max_length=120)
    code: str = Field(max_length=60)
    description: str | None = Field(default=None, max_length=500)
    color: str | None = Field(
        default=None,
        max_length=7,
        regex=r"^#(?:[0-9a-fA-F]{3}){1,2}$",
    )
    is_active: bool = True


class EventAccessLevelUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=120)
    code: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=500)
    color: str | None = Field(
        default=None,
        max_length=7,
        regex=r"^#(?:[0-9a-fA-F]{3}){1,2}$",
    )
    is_active: bool | None = None


class EventAccessLevelResponse(SQLModel):
    id: int
    event_id: int
    name: str
    code: str
    description: str | None = None
    color: str | None = None
    is_active: bool
