from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from app.core.dependencies import (
    get_current_user,
    get_current_organization,
    get_current_membership,
    require_organization_admin,
    require_organization_owner,
)

from app.database.session import SessionDep
from app.models.event import Event, EventCreate, EventStatus, EventUpdate, EventResponse
from app.models.user import User

router = APIRouter()

@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    event_data: EventCreate,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Check if the user is an admin or owner of the organization
    current_membership = get_current_membership(current_user=current_user, db=db)
    require_organization_admin(current_membership=current_membership)

    # Create the event
    new_event = Event(
        name=event_data.name,
        description=event_data.description,
        start_time=event_data.start_time,
        end_time=event_data.end_time,
        organization_id=current_membership.organization_id,
        created_by_user_id=current_user.id
    )

    # validate event date before saving
    if event_data.end_time <= event_data.start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Event end time must be after start time",
        )

    if event_data.registration_opens_at and event_data.registration_closes_at:
        if event_data.registration_closes_at <= event_data.registration_opens_at:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Registration close time must be after registration open time",
            )

    if event_data.registration_opens_at and event_data.start_time:
        if event_data.registration_opens_at >= event_data.start_time:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Registration open time must be before event start time",
            )

    if event_data.registration_closes_at:
        if event_data.registration_closes_at > event_data.start_time:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Registration must close before the event starts",
            )
        
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return new_event

@router.get("/events/{event_id}", response_model=EventResponse)
def get_event(
    event_id: int,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Check if the user is a member of the organization
    current_membership = get_current_membership(current_user=current_user, db=db)

    # Retrieve the event
    statement = select(Event).where(
        Event.id == event_id,
        Event.organization_id == current_membership.organization_id,
    )
    event = db.exec(statement).first()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return event

# retrieve all events for the organization
@router.get("/events", response_model=list[EventResponse])
def get_events(
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Check if the user is a member of the organization
    current_membership = get_current_membership(current_user=current_user, db=db)

    # Retrieve all events for the organization
    statement = select(Event).where(
        Event.organization_id == current_membership.organization_id,
    )
    events = db.exec(statement).all()

    return events

# update an event

@router.patch("/events/{event_id}", response_model=EventResponse)
def update_event(
    event_id: int,
    event_data: EventUpdate,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Check organization membership and permissions
    current_membership = get_current_membership(
        current_user=current_user,
        db=db,
    )

    require_organization_admin(
        current_membership=current_membership
    )

    # Retrieve event belonging to the user's organization
    statement = select(Event).where(
        Event.id == event_id,
        Event.organization_id == current_membership.organization_id,
    )

    event = db.exec(statement).first()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    updates = event_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No event fields provided for update",
        )

    event.sqlmodel_update(updates)

    if event.end_time <= event.start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Event end time must be after start time",
        )

    if (
        event.registration_opens_at
        and event.registration_closes_at
    ):
        if (
            event.registration_closes_at
            <= event.registration_opens_at
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Registration close time must be after registration open time",
            )

    if event.registration_opens_at:
        if event.registration_opens_at >= event.start_time:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Registration open time must be before event start time",
            )

    if event.registration_closes_at:
        if event.registration_closes_at > event.start_time:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Registration must close before the event starts",
            )

    db.add(event)
    db.commit()
    db.refresh(event)

    return event


# delete an event
@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Check if the user is an admin or owner of the organization
    current_membership = get_current_membership(current_user=current_user, db=db)
    require_organization_admin(current_membership=current_membership)

    # Retrieve the event
    statement = select(Event).where(
        Event.id == event_id,
        Event.organization_id == current_membership.organization_id,
    )
    event = db.exec(statement).first()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    if event.status == EventStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Event is already archived",
            )
    
    event.status = EventStatus.ARCHIVED

    

    db.add(event)
    db.commit()

    return None

