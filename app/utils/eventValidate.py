from fastapi import HTTPException, status
from sqlmodel import select

from app.database.session import SessionDep
from app.models.event import Event


def validate_event_for_publishing(event: Event):

    if not event.name:
        raise HTTPException(
            status_code=422,
            detail="Event name is required",
        )

    if not event.slug:
        raise HTTPException(
            status_code=422,
            detail="Event slug is required",
        )

    if not event.start_at or not event.end_at:
        raise HTTPException(
            status_code=422,
            detail="Event start and end times are required",
        )

    if event.end_at <= event.start_at:
        raise HTTPException(
            status_code=422,
            detail="Event end time must be after start time",
        )

    if (
        event.registration_opens_at
        and event.registration_closes_at
        and event.registration_closes_at
        <= event.registration_opens_at
    ):
        raise HTTPException(
            status_code=422,
            detail="Registration close time must be after registration open time",
        )

    if (
        event.registration_opens_at
        and event.registration_opens_at >= event.start_at
    ):
        raise HTTPException(
            status_code=422,
            detail="Registration must open before the event starts",
        )

    if (
        event.registration_closes_at
        and event.registration_closes_at >= event.start_at
    ):
        raise HTTPException(
            status_code=422,
            detail="Registration must close before the event starts",
        )


def validate_event_slug(
    event: Event,
    db: SessionDep,
):
    statement = select(Event).where(
        Event.organization_id == event.organization_id,
        Event.slug == event.slug,
        Event.id != event.id,
    )

    existing_event = db.exec(statement).first()

    if existing_event:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An event with this slug already exists in your organization",
        )