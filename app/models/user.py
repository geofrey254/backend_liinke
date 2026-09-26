from typing import Optional
from sqlmodel import Field, SQLModel

from datetime import datetime,timezone

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    full_name: Optional[str] = None
    hashed_password: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=lambda:datetime.now(timezone.utc), nullable=False)

class UserCreate(SQLModel):
    username: str
    email: str
    full_name: Optional[str] = None
    password: str

class UserRead(SQLModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    updated_at: datetime

class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

class UserResponse(SQLModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    updated_at: datetime