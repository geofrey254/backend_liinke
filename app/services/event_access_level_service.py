
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.event import Event
from app.models.eventAccessLevel import (
    EventAccessLevel,
    EventAccessLevelCreate,
    EventAccessLevelUpdate,
)


def get_event_for_org(
    db: Session,
    event_id: int,
    organization_id: int,
) -> Event:
    event = db.exec(
        select(Event).where(
            Event.id == event_id,
            Event.organization_id == organization_id,
        )
    ).first()

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    return event


def create_access_level(
    db: Session,
    event_id: int,
    organization_id: int,
    data: EventAccessLevelCreate,
) -> EventAccessLevel:

    get_event_for_org(db, event_id, organization_id)

    access_level = EventAccessLevel(
        **data.model_dump(),
        event_id=event_id,
    )

    db.add(access_level)

    try:
        db.commit()
        db.refresh(access_level)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An access level with this code already exists for this event",
        ) from None

    return access_level


def get_access_level(
    db: Session,
    event_id: int,
    organization_id: int,
    access_level_id: int,
) -> EventAccessLevel:

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
            detail="Access level not found",
        )

    return access_level


def get_access_levels(
    db: Session,
    event_id: int,
    organization_id: int,
) -> list[EventAccessLevel]:

    get_event_for_org(db, event_id, organization_id)

    return db.exec(
        select(EventAccessLevel).where(
            EventAccessLevel.event_id == event_id
        )
    ).all()


def update_access_level(
    db: Session,
    event_id: int,
    organization_id: int,
    access_level_id: int,
    data: EventAccessLevelUpdate,
) -> EventAccessLevel:

    access_level = get_access_level(
        db,
        event_id,
        organization_id,
        access_level_id,
    )

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No update fields provided",
        )

    for key, value in update_data.items():
        setattr(access_level, key, value)

    try:
        db.add(access_level)
        db.commit()
        db.refresh(access_level)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An access level with this code already exists for this event",
        ) from None

    return access_level


def deactivate_access_level(
    db: Session,
    event_id: int,
    organization_id: int,
    access_level_id: int,
) -> EventAccessLevel:

    access_level = get_access_level(
        db,
        event_id,
        organization_id,
        access_level_id,
    )

    access_level.is_active = False

    db.add(access_level)
    db.commit()
    db.refresh(access_level)

    return access_level
