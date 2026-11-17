
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import (
    get_current_user,
    get_current_membership,
    require_organization_admin,
)

from app.database.session import SessionDep

from app.models.eventAccessLevel import (
    EventAccessLevelCreate,
    EventAccessLevelUpdate,
    EventAccessLevelResponse,
)

from app.models.organizationMembership import OrganizationMembership
from app.models.user import User

from app.services.event_access_level_service import (
    create_access_level,
    deactivate_access_level,
    get_access_level,
    get_access_levels,
    update_access_level,
)

router = APIRouter()


@router.post(
    "/events/{event_id}/access-levels",
    response_model=EventAccessLevelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event_access_level(
    event_id: int,
    data: EventAccessLevelCreate,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    return create_access_level(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
        data=data,
    )


@router.get(
    "/events/{event_id}/access-levels/{access_level_id}",
    response_model=EventAccessLevelResponse,
)
def get_event_access_level(
    event_id: int,
    access_level_id: int,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
):
    return get_access_level(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
        access_level_id=access_level_id,
    )


@router.get(
    "/events/{event_id}/access-levels",
    response_model=list[EventAccessLevelResponse],
)
def get_event_access_levels(
    event_id: int,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
):
    return get_access_levels(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
    )


@router.patch(
    "/events/{event_id}/access-levels/{access_level_id}",
    response_model=EventAccessLevelResponse,
)
def update_event_access_level(
    event_id: int,
    access_level_id: int,
    data: EventAccessLevelUpdate,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    return update_access_level(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
        access_level_id=access_level_id,
        data=data,
    )


@router.delete(
    "/events/{event_id}/access-levels/{access_level_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_event_access_level(
    event_id: int,
    access_level_id: int,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    deactivate_access_level(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
        access_level_id=access_level_id,
    )

    return None
