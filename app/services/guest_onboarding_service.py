import json
import re
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.event import Event, EventStatus
from app.models.eventAccessLevel import EventAccessLevel
from app.models.eventGuest import EventGuest, EventGuestResponse, EventGuestStatus, InvitationStatus
from app.models.eventCustomField import EventCustomField, EventCustomFieldType
from app.models.guest import Guest, GuestCreate


def normalize_identity(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().casefold())


def find_possible_duplicates(
    db: Session,
    organization_id: int,
    guest_data: GuestCreate,
) -> list[Guest]:
    candidates = db.exec(
        select(Guest).where(Guest.organization_id == organization_id)
    ).all()
    email = normalize_identity(guest_data.email)
    phone = normalize_identity(guest_data.phone)
    name = normalize_identity(guest_data.full_name)
    return [
        guest for guest in candidates
        if (
            (email and normalize_identity(guest.email) == email)
            or (phone and normalize_identity(guest.phone) == phone)
            or (name and normalize_identity(guest.full_name) == name)
        )
    ]


def get_event_for_org(db: Session, event_id: int, organization_id: int) -> Event:
    event = db.exec(
        select(Event).where(
            Event.id == event_id,
            Event.organization_id == organization_id,
        )
    ).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status in {EventStatus.ARCHIVED, EventStatus.CANCELLED, EventStatus.COMPLETED}:
        raise HTTPException(status_code=409, detail="Guests cannot be registered for this event")
    return event


def validate_access_level(
    db: Session,
    event_id: int,
    access_level_id: int | None,
) -> EventAccessLevel | None:
    if access_level_id is None:
        return None
    access_level = db.exec(
        select(EventAccessLevel).where(
            EventAccessLevel.id == access_level_id,
            EventAccessLevel.event_id == event_id,
        )
    ).first()
    if access_level is None:
        raise HTTPException(status_code=422, detail="Access level does not belong to this event")
    if not access_level.is_active:
        raise HTTPException(status_code=422, detail="Archived access levels cannot be assigned")
    return access_level


def register_guest(
    db: Session,
    organization_id: int,
    user_id: int,
    event_id: int,
    guest_id: int,
    access_level_id: int | None,
    custom_field_values: dict | None = None,
    status: EventGuestStatus = EventGuestStatus.REGISTERED,
) -> EventGuest:
    event = get_event_for_org(db, event_id, organization_id)
    validate_access_level(db, event_id, access_level_id)
    if event.capacity is not None:
        registrations = db.exec(
            select(EventGuest).where(
                EventGuest.event_id == event_id,
                EventGuest.registration_status != EventGuestStatus.CANCELLED,
            )
        ).all()
        if len(registrations) >= event.capacity:
            raise HTTPException(status_code=409, detail="Event capacity has been reached")
    guest = db.exec(
        select(Guest).where(
            Guest.id == guest_id,
            Guest.organization_id == organization_id,
        )
    ).first()
    if guest is None:
        raise HTTPException(status_code=404, detail="Guest not found")
    validate_custom_fields(db, event_id, custom_field_values or {})
    existing = db.exec(
        select(EventGuest).where(
            EventGuest.event_id == event_id,
            EventGuest.guest_id == guest_id,
        )
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Guest is already registered for this event")
    now = datetime.now(timezone.utc)
    registration = EventGuest(
        event_id=event_id,
        guest_id=guest_id,
        access_level_id=access_level_id,
        custom_field_values=json.dumps(custom_field_values) if custom_field_values else None,
        registration_status=status,
        invitation_status=InvitationStatus.PENDING,
        registered_at=now,
        approved_at=now if status == EventGuestStatus.APPROVED else None,
        created_by=user_id,
    )
    db.add(registration)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Guest is already registered for this event") from None
    return registration


def validate_custom_fields(db: Session, event_id: int, values: dict) -> None:
    definitions = db.exec(
        select(EventCustomField).where(
            EventCustomField.event_id == event_id,
            EventCustomField.is_active.is_(True),
        )
    ).all()
    by_key = {field.field_key: field for field in definitions}
    unknown = set(values) - set(by_key)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown event custom fields: {', '.join(sorted(unknown))}",
        )
    for field in definitions:
        value = values.get(field.field_key)
        if field.required and (value is None or value == "" or value == []):
            raise HTTPException(status_code=422, detail=f"Custom field '{field.field_key}' is required")
        if value is None:
            continue
        try:
            if field.field_type == EventCustomFieldType.NUMBER:
                float(value)
            elif field.field_type == EventCustomFieldType.DATE:
                date.fromisoformat(str(value))
            elif field.field_type in {EventCustomFieldType.CHECKBOX, EventCustomFieldType.BOOLEAN}:
                if not isinstance(value, bool):
                    raise ValueError
            elif field.field_type == EventCustomFieldType.EMAIL and "@" not in str(value):
                raise ValueError
            elif field.field_type == EventCustomFieldType.MULTI_SELECT:
                if not isinstance(value, list):
                    raise ValueError
            elif field.field_type == EventCustomFieldType.DROPDOWN:
                options = json.loads(field.options or "[]")
                if value not in options:
                    raise ValueError
        except (TypeError, ValueError, json.JSONDecodeError):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid value for custom field '{field.field_key}'",
            ) from None
