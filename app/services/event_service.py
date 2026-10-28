from sqlmodel import select

from fastapi import HTTPException

from app.models.event import Event, EventCreate, EventResponse
from app.models.eventAccessLevel import EventAccessLevel, EventAccessLevelCreate, EventAccessLevelResponse
from app.models.eventAccessLevelZone import EventAccessLevelZone, EventAccessLevelZoneCreate, EventAccessLevelZoneResponse
from app.models.securityZone import EventSecurityZone, EventSecurityZoneCreate, EventSecurityZoneResponse

from app.database.session import SessionDep

def create_event_service(event_data: EventCreate, db: SessionDep) -> EventResponse:
    new_event = Event(
        name=event_data.name,
        slug=event_data.slug,
        description=event_data.description,
        start_at=event_data.start_at,
        end_at=event_data.end_at,
        location=event_data.location,
        capacity=event_data.capacity,
        registration_enabled=event_data.registration_enabled,
        organization_id=event_data.organization_id
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return new_event

def get_event_by_id_service(event_id: int, db: SessionDep) -> EventResponse | None:
    event = db.get(Event, event_id)

    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Event with id {event_id} not found"
        )

    return event

def get_events_service(db: SessionDep) -> list[EventResponse]:
    events = db.exec(select(Event)).all()
    return events

def create_event_access_level_service(event_access_level_data: EventAccessLevelCreate, db: SessionDep) -> EventAccessLevelResponse:
    new_event_access_level = EventAccessLevel(
        event_id=event_access_level_data.event_id,
        name=event_access_level_data.name,
        code=event_access_level_data.code,
        description=event_access_level_data.description,
        is_active=event_access_level_data.is_active
    )

    db.add(new_event_access_level)
    db.commit()
    db.refresh(new_event_access_level)

    return new_event_access_level

def get_event_access_levels_by_event_id_service(event_id: int, db: SessionDep) -> list[EventAccessLevelResponse]:
    event_access_levels = db.exec(
        select(EventAccessLevel).where(EventAccessLevel.event_id == event_id)
    ).all()

    return event_access_levels

def create_event_access_level_zone_service(event_access_level_zone_data: EventAccessLevelZoneCreate, db: SessionDep) -> EventAccessLevelZoneResponse:
    new_event_access_level_zone = EventAccessLevelZone(
        event_access_level_id=event_access_level_zone_data.event_access_level_id,
        security_zone_id=event_access_level_zone_data.security_zone_id,
        is_active=event_access_level_zone_data.is_active
    )

    db.add(new_event_access_level_zone)
    db.commit()
    db.refresh(new_event_access_level_zone)

    return new_event_access_level_zone

def get_event_access_level_zones_by_access_level_id_service(event_access_level_id: int, db: SessionDep) -> list[EventAccessLevelZoneResponse]:
    event_access_level_zones = db.exec(
        select(EventAccessLevelZone).where(EventAccessLevelZone.event_access_level_id == event_access_level_id)
    ).all()

    return event_access_level_zones

def create_event_security_zone_service(event_security_zone_data: EventSecurityZoneCreate, db: SessionDep) -> EventSecurityZoneResponse:
    new_event_security_zone = EventSecurityZone(
        event_id=event_security_zone_data.event_id,
        name=event_security_zone_data.name,
        description=event_security_zone_data.description,
        is_active=event_security_zone_data.is_active
    )

    db.add(new_event_security_zone)
    db.commit()
    db.refresh(new_event_security_zone)

    return new_event_security_zone

def get_event_security_zones_by_event_id_service(event_id: int, db: SessionDep) -> list[EventSecurityZoneResponse]:
    event_security_zones = db.exec(
        select(EventSecurityZone).where(EventSecurityZone.event_id == event_id)
    ).all()

    return event_security_zones
