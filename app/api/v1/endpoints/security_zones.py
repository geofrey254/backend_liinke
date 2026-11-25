from typing import Annotated
from fastapi import APIRouter, Depends, status

from app.core.dependencies import (
    get_current_user,
    get_current_membership,
    require_organization_admin,
)

from app.database.session import SessionDep

from app.models.securityZone import (
    EventSecurityZoneCreate,
    EventSecurityZoneUpdate,
    EventSecurityZoneResponse,   
)

from app.models.organizationMembership import OrganizationMembership
from app.models.user import User

from app.services.security_zone_service import (
    create_security_zone,
    get_security_zone,
    get_security_zones,
    update_security_zone,
    delete_security_zone,
)


router = APIRouter()


@router.post(
    "/events/{event_id}/security-zones",
    response_model=EventSecurityZoneResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event_security_zone(
    event_id: int,
    data: EventSecurityZoneCreate,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    return create_security_zone(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
        data=data,
    )

@router.get(
    "/events/{event_id}/security-zones/{zone_id}",
    response_model=EventSecurityZoneResponse,
)
def get_event_security_zone(    
    event_id: int,
    zone_id: int,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
):
    return get_security_zone(
        db=db,
        event_id=event_id,
        zone_id=zone_id,
        organization_id=membership.organization_id,
    )

@router.get(
    "/events/{event_id}/security-zones",
    response_model=list[EventSecurityZoneResponse],
)
def get_event_security_zones(    
    event_id: int,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
):
    return get_security_zones(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
    )

@router.patch(
    "/events/{event_id}/security-zones/{zone_id}",
    response_model=EventSecurityZoneResponse,
)
def update_event_security_zone(
    event_id: int,
    zone_id: int,
    data: EventSecurityZoneUpdate,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    return update_security_zone(
        db=db,
        event_id=event_id,
        organization_id=membership.organization_id,
        data=data,
        zone_id=zone_id,
    )

@router.delete(
    "/events/{event_id}/security-zones/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_event_security_zone(
    event_id: int,
    zone_id: int,
    db: SessionDep,
    membership: Annotated[
        OrganizationMembership,
        Depends(get_current_membership),
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    return delete_security_zone(
        db=db,
        event_id=event_id,
        zone_id=zone_id,
        organization_id=membership.organization_id,
    )