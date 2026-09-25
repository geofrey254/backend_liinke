from typing import Optional
from sqlmodel import Field, SQLModel

from datetime import datetime,timezone

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    hashed_password: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=lambda:datetime.now(timezone.utc), nullable=False)