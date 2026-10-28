
from sqlmodel import Field, SQLModel
from sqlalchemy import UniqueConstraint


class EventSecurityZone(SQLModel, table=True):
    __tablename__ = "event_security_zones"

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "code",
            name="uq_event_zone_code",
        ),
    )

    id: int | None = Field(
        default=None,
        primary_key=True,
    )

    event_id: int = Field(
        foreign_key="events.id",
        nullable=False,
        index=True,
    )

    name: str = Field(
        max_length=120,
        nullable=False,
    )

    code: str = Field(
        max_length=60,
        nullable=False,
    )

    description: str | None = Field(
        default=None,
        max_length=500,
    )

    is_active: bool = Field(default=True)


class EventSecurityZoneCreate(SQLModel):
    event_id: int
    name: str
    code: str
    description: str | None = None
    is_active: bool = True

class EventSecurityZoneResponse(SQLModel):
    id: int
    event_id: int
    name: str
    code: str
    description: str | None = None
    is_active: bool

class EventSecurityZoneUpdate(SQLModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    is_active: bool | None = None