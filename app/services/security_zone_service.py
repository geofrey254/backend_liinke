from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.event import Event
from app.models.securityZone import EventSecurityZone, EventSecurityZoneCreate, EventSecurityZoneUpdate
from app.services.event_access_level_service import get_event_for_org


def create_security_zone(
    db: Session,
    event_id: int,
    organization_id: int,
    data: EventSecurityZoneCreate,
) -> EventSecurityZone:
    get_event_for_org(db, event_id, organization_id)

    security_zone = EventSecurityZone(
        **data.model_dump(),
        event_id=event_id,
        organization_id=organization_id,
    )

    db.add(security_zone)

    try:
        db.commit()
        db.refresh(security_zone)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A security zone with this name already exists for this event",
        ) from None

    return security_zone

def get_security_zone(
    db: Session,
    event_id: int,
    organization_id: int,
) -> EventSecurityZone:
    security_zone = db.exec(
        select(EventSecurityZone).where(
            EventSecurityZone.event_id == event_id,
            EventSecurityZone.organization_id == organization_id,
        )
    ).first()

    if security_zone is None:
        raise HTTPException(
            status_code=404,
            detail="Security zone not found for this event",
        )

    return security_zone

def update_security_zone(
    db: Session,
    event_id: int,
    organization_id: int,
    data: EventSecurityZoneUpdate,
) -> EventSecurityZone:
    security_zone = get_security_zone(db, event_id, organization_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(security_zone, key, value)

    try:
        db.commit()
        db.refresh(security_zone)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A security zone with this name already exists for this event",
        ) from None

    return security_zone

def delete_security_zone(
    db: Session,
    event_id: int,
    organization_id: int,
) -> None:
    security_zone = get_security_zone(db, event_id, organization_id)

    db.delete(security_zone)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete security zone as it is referenced by other records",
        ) from None