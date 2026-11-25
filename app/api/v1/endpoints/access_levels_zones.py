
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import (
    get_current_membership,
    require_organization_admin,
)
from app.database.session import SessionDep

from app.models.eventAccessLevelZone import (
    EventAccessLevelZoneCreate,
    EventAccessLevelZoneResponse,
)
from app.models.organizationMembership import OrganizationMembership

from app.services.event_access_level_zone_service import (
    create_access_level_zone,
    get_access_level_zones,
    delete_access_level_zone,
)


router = APIRouter()


@router.post(
    "/events/{event_id}/access-level-zones",
    response_model=EventAccessLevelZoneResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event_access_level_zone(
    event_id: int,
    data: EventAccessLevelZoneCreate,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[
        None,
        Depends(require_organization_admin),
    ],
):
    return create_access_level_zone(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
        data=data,
    )


@router.get(
    "/events/{event_id}/access-level-zones",
    response_model=list[EventAccessLevelZoneResponse],
)
def get_event_access_level_zones(
    event_id: int,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
):
    return get_access_level_zones(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
    )


@router.delete(
    "/events/{event_id}/access-level-zones/{access_level_id}/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_event_access_level_zone(
    event_id: int,
    access_level_id: int,
    zone_id: int,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[
        None,
        Depends(require_organization_admin),
    ],
):
    delete_access_level_zone(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
        access_level_id=access_level_id,
        zone_id=zone_id,
    )

    return None
