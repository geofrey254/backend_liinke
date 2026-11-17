from typing import Annotated
from fastapi import APIRouter, Depends, status
from app.core.dependencies import (
    get_current_membership,
    require_organization_admin,
)
from app.database.session import SessionDep
from app.models.eventAccessLevelZone import (
    EventAccessLevelZoneCreate,
    EventAccessLevelZoneUpdate,
    EventAccessLevelZoneResponse,
)
from app.models.organizationMembership import OrganizationMembership
from app.models.user import User
from app.services.event_access_level_zone_service import (
    create_access_level_zone,
    get_access_level_zone,
    update_access_level_zone,
    deactivate_access_level_zone,
)

router = APIRouter()

@router.post(
    "/events/{event_id}/access-level-zones",
    response_model=EventAccessLevelZoneResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event_access_level_zone(
    event_id: int,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    return create_access_level_zone(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
    )

@router.get(
    "/events/{event_id}/access-level-zones",
    response_model=EventAccessLevelZoneResponse,
)
def get_event_access_level_zone(
    event_id: int,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
):
    return get_access_level_zone(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
    )

@router.put(
    "/events/{event_id}/access-level-zones",
    response_model=EventAccessLevelZoneResponse,
)
def update_event_access_level_zone(
    event_id: int,
    data: EventAccessLevelZoneUpdate,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    return update_access_level_zone(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
        data=data,
    )

@router.delete(
    "/events/{event_id}/access-level-zones",
    response_model=EventAccessLevelZoneResponse,
)
def delete_event_access_level_zone(
    event_id: int,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    return deactivate_access_level_zone(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
    )