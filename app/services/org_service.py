from sqlmodel import select

from fastapi import HTTPException

from app.database.session import SessionDep
from app.models.organization import Organization, OrganizationCreate, OrganizationResponse

def create_orgs_service(org_data:OrganizationCreate, db: SessionDep) -> OrganizationResponse:
    existing_org = db.exec(select(Organization).where(Organization.slug == org_data.slug)).first()
    if existing_org:
        raise HTTPException(
            status_code=400,
            detail=f"Organization with slug {org_data.slug} already exists"
        )
    
    new_organization = Organization(**org_data.model_dump())

    db.add(new_organization)
    db.commit()
    db.refresh(new_organization)

    return new_organization

def get_orgs_service(db: SessionDep) -> list[OrganizationResponse]:
    organizations = db.exec(select(Organization)).all()
    return organizations

def get_orgs_by_id_service(org_id: int, db: SessionDep) -> OrganizationResponse | None:
    organization = db.get(Organization, org_id)

    if not organization:
        raise HTTPException(
            status_code=404,
            detail=f"Organization with id {org_id} not found"
        )
    
    return organization