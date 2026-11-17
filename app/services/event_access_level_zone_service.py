from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.event import Event
from app.models.eventAccessLevelZone import (
    EventAccessLevelZone,
    EventAccessLevelZoneCreate,
    EventAccessLevelZoneUpdate,
)

from app.services.event_access_level_service import get_event_for_org

def create_access_level_zone(
        db: Session,
        event_id: int,
        organization_id: int,
) -> EventAccessLevelZone:
    get_event_for_org(db, event_id, organization_id)

    access_level_zone = EventAccessLevelZone(
        event_id=event_id,
        organization_id=organization_id,
    )

    db.add(access_level_zone)

    try:
        db.commit()
        db.refresh(access_level_zone)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An access level zone already exists for this event",
        ) from None

    return access_level_zone

def get_access_level_zone(
        db: Session,
        event_id: int,
        organization_id: int,
) -> EventAccessLevelZone:
    access_level_zone = db.exec(
        select(EventAccessLevelZone).where(
            EventAccessLevelZone.event_id == event_id,
            EventAccessLevelZone.organization_id == organization_id,
        )
    ).first()

    if access_level_zone is None:
        raise HTTPException(
            status_code=404,
            detail="Access level zone not found for this event",
        )

    return access_level_zone

def update_access_level_zone(
        db: Session,
        event_id: int,
        organization_id: int,
        data: EventAccessLevelZoneUpdate,
) -> EventAccessLevelZone:
    access_level_zone = get_access_level_zone(db, event_id, organization_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(access_level_zone, key, value)

    db.add(access_level_zone)

    try:
        db.commit()
        db.refresh(access_level_zone)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An access level zone already exists for this event",
        ) from None

    return access_level_zone

def deactivate_access_level_zone(
        db: Session,
        event_id: int,
        organization_id: int,
) -> EventAccessLevelZone:
    access_level_zone = get_access_level_zone(db, event_id, organization_id)

    access_level_zone.is_active = False

    db.add(access_level_zone)

    try:
        db.commit()
        db.refresh(access_level_zone)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An access level zone already exists for this event",
        ) from None

    return access_level_zone