from datetime import datetime

from pydantic import BaseModel, EmailStr


class OrganisationBase(BaseModel):
	name: str
	logo: str | None = None
	email: EmailStr | None = None
	phone: str | None = None
	website: str | None = None
	address: str | None = None
	description: str | None = None
	subscription_plan: str = "free"
	is_active: bool = True


class OrganisationCreate(OrganisationBase):
	pass


class OrganisationUpdate(BaseModel):
	name: str | None = None
	logo: str | None = None
	email: EmailStr | None = None
	phone: str | None = None
	website: str | None = None
	address: str | None = None
	description: str | None = None
	subscription_plan: str | None = None
	is_active: bool | None = None


class OrganisationRead(OrganisationBase):
	id: int
	created_at: datetime
	updated_at: datetime

	class Config:
		from_attributes = True
