
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.eventAccessLevel import EventAccessLevel
from app.models.securityZone import EventSecurityZone
from app.models.eventAccessLevelZone import (
    EventAccessLevelZone,
    EventAccessLevelZoneCreate,
)
from app.services.event_access_level_service import get_event_for_org


def get_access_level_and_zone(
    db: Session,
    event_id: int,
    organization_id: int,
    access_level_id: int,
    zone_id: int,
) -> tuple[EventAccessLevel, EventSecurityZone]:
    """
    Verify that the event belongs to the organization
    and that both records belong to that event.
    """

    get_event_for_org(db, event_id, organization_id)

    access_level = db.exec(
        select(EventAccessLevel).where(
            EventAccessLevel.id == access_level_id,
            EventAccessLevel.event_id == event_id,
        )
    ).first()

    if access_level is None:
        raise HTTPException(
            status_code=404,
            detail="Access level not found for this event",
        )

    zone = db.exec(
        select(EventSecurityZone).where(
            EventSecurityZone.id == zone_id,
            EventSecurityZone.event_id == event_id,
        )
    ).first()

    if zone is None:
        raise HTTPException(
            status_code=404,
            detail="Security zone not found for this event",
        )

    return access_level, zone


def create_access_level_zone(
    db: Session,
    event_id: int,
    organization_id: int,
    data: EventAccessLevelZoneCreate,
) -> EventAccessLevelZone:

    get_access_level_and_zone(
        db=db,
        event_id=event_id,
        organization_id=organization_id,
        access_level_id=data.access_level_id,
        zone_id=data.zone_id,
    )

    relationship = EventAccessLevelZone(
        access_level_id=data.access_level_id,
        zone_id=data.zone_id,
    )

    db.add(relationship)

    try:
        db.commit()
        db.refresh(relationship)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This access level is already assigned to this security zone",
        ) from None

    return relationship


def get_access_level_zones(
    db: Session,
    event_id: int,
    organization_id: int,
) -> list[EventAccessLevelZone]:

    get_event_for_org(db, event_id, organization_id)

    statement = (
        select(EventAccessLevelZone)
        .join(
            EventAccessLevel,
            EventAccessLevel.id
            == EventAccessLevelZone.access_level_id,
        )
        .where(EventAccessLevel.event_id == event_id)
    )

    return db.exec(statement).all()


def delete_access_level_zone(
    db: Session,
    event_id: int,
    organization_id: int,
    access_level_id: int,
    zone_id: int,
) -> None:

    get_access_level_and_zone(
        db=db,
        event_id=event_id,
        organization_id=organization_id,
        access_level_id=access_level_id,
        zone_id=zone_id,
    )

    relationship = db.exec(
        select(EventAccessLevelZone).where(
            EventAccessLevelZone.access_level_id == access_level_id,
            EventAccessLevelZone.zone_id == zone_id,
        )
    ).first()

    if relationship is None:
        raise HTTPException(
            status_code=404,
            detail="Access permission not found",
        )

    db.delete(relationship)
    db.commit()
