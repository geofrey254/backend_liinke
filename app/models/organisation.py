from datetime import datetime

from sqlmodel import Field, SQLModel


class OrganisationBase(SQLModel):
	name: str
	logo: str | None = None
	email: str | None = None
	phone: str | None = None
	website: str | None = None
	address: str | None = None
	description: str | None = None
	subscription_plan: str = Field(default="free", index=True)
	is_active: bool = Field(default=True, index=True)


class Organisation(OrganisationBase, table=True):
	id: int | None = Field(default=None, primary_key=True)
	created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
	updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
