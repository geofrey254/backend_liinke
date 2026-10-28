from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class EventAccessLevelZone(SQLModel, table=True):
    __tablename__ = "event_access_level_zones"

    __table_args__ = (
        UniqueConstraint(
            "access_level_id", "zone_id",
            name="uq_access_level_zone",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)

    access_level_id: int = Field(
        foreign_key="event_access_levels.id",
        nullable=False,
        index=True,
    )

    zone_id: int = Field(
        foreign_key="event_security_zones.id",
        nullable=False,
        index=True,
    )

class EventAccessLevelZoneCreate(SQLModel):
    access_level_id: int
    zone_id: int

class EventAccessLevelZoneResponse(SQLModel):
    id: int
    access_level_id: int
    zone_id: int

class EventAccessLevelZoneUpdate(SQLModel):
    access_level_id: int | None = None
    zone_id: int | None = None