from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import (
    get_current_user,
    get_current_membership,
    require_organization_admin,
)

from app.database.session import SessionDep
from app.models.event import Event, EventCreate, EventStatus, EventUpdate, EventResponse, utc_now
from app.models.organizationMembership import OrganizationMembership
from app.models.user import User
from app.utils.eventValidate import validate_event_for_publishing, validate_event_slug

router = APIRouter()

@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    event_data: EventCreate,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
    current_membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):

    # Create the event
    new_event = Event(
        **event_data.model_dump(),
        organization_id=current_membership.organization_id,
        created_by_user_id=current_user.id,
        status=EventStatus.DRAFT,
    )
        
    try:
        db.add(new_event)
        db.commit()
        db.refresh(new_event)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An event with this slug already exists in your organization",
        )

    return new_event

@router.post(
    "/events/{event_id}/publish",
    response_model=EventResponse,
)
def publish_event(
    event_id: int,
    db: SessionDep,
    current_membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    statement = select(Event).where(
        Event.id == event_id,
        Event.organization_id == current_membership.organization_id,
    )

    event = db.exec(statement).first()

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    if event.status != EventStatus.DRAFT:
        raise HTTPException(
            status_code=409,
            detail="Only draft events can be published",
        )

    validate_event_slug(event, db)

    validate_event_for_publishing(event)

    event.status = EventStatus.PUBLISHED
    event.published_at = utc_now()

    try:
        db.add(event)
        db.commit()
        db.refresh(event)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An event with this slug already exists in your organization",
        )

    return event

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
    current_membership: Annotated[
            OrganizationMembership,
            Depends(get_current_membership),
        ],
        _: Annotated[None, Depends(require_organization_admin)],
    event_status: EventStatus | None = Query(
        default=None,
        alias="status",
    ),
    
):

    statement = select(Event).where(
        Event.organization_id == current_membership.organization_id,
    )

    if event_status is not None:
        statement = statement.where(
            Event.status == event_status
        )

    events = db.exec(statement).all()

    return events

# update an event

@router.patch("/events/{event_id}", response_model=EventResponse)
def update_event(
    event_id: int,
    event_data: EventUpdate,
    db: SessionDep,
    current_membership: Annotated[
                OrganizationMembership,
                Depends(get_current_membership),
            ],
            _: Annotated[None, Depends(require_organization_admin)],
):
    

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

    if event.status == EventStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived events cannot be updated",
        )

    updates = event_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No event fields provided for update",
        )

    # Apply the updates
    event.sqlmodel_update(updates)

    # Check slug uniqueness
    validate_event_slug(event, db)

    # Validate date range only when both dates exist
    if event.start_at and event.end_at:
        if event.end_at <= event.start_at:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Event end time must be after event start time",
            )

    # Published events must satisfy all publication requirements
    if event.status == EventStatus.PUBLISHED:
        validate_event_for_publishing(event)

    # Save changes
    try:
        db.add(event)
        db.commit()
        db.refresh(event)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An event with this slug already exists in your organization",
        )

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

