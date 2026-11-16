from enum import StrEnum

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class EventCustomFieldType(StrEnum):
    TEXT = "text"
    LONG_TEXT = "long_text"
    EMAIL = "email"
    PHONE = "phone"
    NUMBER = "number"
    DATE = "date"
    DROPDOWN = "dropdown"
    MULTI_SELECT = "multi_select"
    CHECKBOX = "checkbox"
    BOOLEAN = "boolean"


class EventCustomField(SQLModel, table=True):
    __tablename__ = "event_custom_fields"
    __table_args__ = (
        UniqueConstraint("event_id", "field_key", name="uq_event_custom_field_key"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", nullable=False, index=True)
    field_key: str = Field(max_length=100, nullable=False)
    label: str = Field(max_length=200, nullable=False)
    field_type: EventCustomFieldType = Field(nullable=False)
    required: bool = Field(default=False, nullable=False)
    options: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    is_active: bool = Field(default=True, nullable=False)


class EventCustomFieldCreate(SQLModel):
    field_key: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    field_type: EventCustomFieldType
    required: bool = False
    options: list[str] | None = None


class EventCustomFieldResponse(SQLModel):
    id: int
    event_id: int
    field_key: str
    label: str
    field_type: EventCustomFieldType
    required: bool
    options: list[str] | None
    is_active: bool
