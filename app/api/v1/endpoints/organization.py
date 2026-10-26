
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.core.dependencies import (
    get_current_user,
    get_current_organization,
    get_current_membership,
    require_organization_admin,
    require_organization_owner,
)
from app.database.session import SessionDep
from app.models.user import User
from app.models.organization import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    CurrentOrganizationResponse
)
from app.models.organizationMembership import (
    OrganizationMembership,
    OrganizationRole,
    OrganizationMembershipAdminCreate,
    OrganizationMembershipRoleUpdate,
    OrganizationMembershipResponse,
)

router = APIRouter()

# 1. Create an organization and assign its creator as owner.
@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    org_data: OrganizationCreate,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
):
    existing_membership = db.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == current_user.id,
        )
    ).first()

    if existing_membership is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already associated with an organization",
        )

    organization = Organization(
        name=org_data.name,
        slug=org_data.slug,
        category=org_data.category,
        website_url=org_data.website_url,
        logo_url=org_data.logo_url,
        timezone=org_data.timezone,
        is_active=True,
    )

    try:
        db.add(organization)
        db.flush()  # Obtain the new organization ID before committing.

        membership = OrganizationMembership(
            user_id=current_user.id,
            organization_id=organization.id,
            role=OrganizationRole.OWNER,
        )

        db.add(membership)

        db.commit()
        db.refresh(organization)

        return organization

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create organization. The slug may already exist.",
        ) from None


# 2. Retrieve the current organization.
@router.get("/me", response_model=CurrentOrganizationResponse)
def read_current_organization(
    organization: Annotated[
        Organization, Depends(get_current_organization)
    ],
    membership: Annotated[
        OrganizationMembership, Depends(get_current_membership)
    ],
):
    return {
        "organization": organization,
        "membership": membership
    }


# 3. Update organization details.
@router.patch("/me", response_model=OrganizationResponse)
def update_organization(
    org_data: OrganizationUpdate,
    db: SessionDep,
    organization: Annotated[
        Organization, Depends(get_current_organization)
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    # Do not allow organization deactivation through this endpoint.
    update_data = org_data.model_dump(
        exclude_unset=True,
        exclude={"is_active"},
    )

    for field, value in update_data.items():
        setattr(organization, field, value)

    try:
        db.add(organization)
        db.commit()
        db.refresh(organization)
        return organization

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization update conflicts with existing data.",
        ) from None


# 4. List current organization members.
@router.get(
    "/me/members",
    response_model=list[OrganizationMembershipResponse],
)
def list_members(
    db: SessionDep,
    organization: Annotated[
        Organization, Depends(get_current_organization)
    ],
    membership: Annotated[
        OrganizationMembership, Depends(get_current_membership)
    ],
):
    statement = select(OrganizationMembership).where(
        OrganizationMembership.organization_id == organization.id
    )
    return db.exec(statement).all()


# 5. Add a member to the current organization.
@router.post(
    "/me/members",
    response_model=OrganizationMembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    membership_data: OrganizationMembershipAdminCreate,
    db: SessionDep,
    organization: Annotated[
        Organization, Depends(get_current_organization)
    ],
    current_membership: Annotated[
        OrganizationMembership, Depends(get_current_membership)
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    if membership_data.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the ownership-transfer workflow to assign an owner.",
        )

    if (
        membership_data.role == OrganizationRole.ADMIN
        and current_membership.role != OrganizationRole.OWNER
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization owner can assign admin privileges.",
        )

    user = db.get(User, membership_data.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    existing = db.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == organization.id,
        )
    ).first()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization",
        )

    # Use an invitation workflow instead if membership requires approval.
    new_membership = OrganizationMembership(
        user_id=user.id,
        organization_id=organization.id,
        role=membership_data.role,
    )

    db.add(new_membership)

    try:
        db.commit()
        db.refresh(new_membership)
        return new_membership

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Membership already exists or conflicts with database constraints.",
        ) from None


# 6. Remove a member.
@router.delete(
    "/me/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    user_id: int,
    db: SessionDep,
    organization: Annotated[
        Organization, Depends(get_current_organization)
    ],
    current_membership: Annotated[
        OrganizationMembership, Depends(get_current_membership)
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    target = db.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization.id,
        )
    ).first()

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if target.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transfer ownership before removing the owner.",
        )

    if (
        target.role == OrganizationRole.ADMIN
        and current_membership.role != OrganizationRole.OWNER
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can remove another admin.",
        )

    db.delete(target)
    db.commit()
    return None


# 7. Update a member's role.
@router.patch(
    "/me/members/{user_id}/role",
    response_model=OrganizationMembershipResponse,
)
def update_member_role(
    user_id: int,
    data: OrganizationMembershipRoleUpdate,
    db: SessionDep,
    organization: Annotated[
        Organization, Depends(get_current_organization)
    ],
    current_membership: Annotated[
        OrganizationMembership, Depends(get_current_membership)
    ],
    _: Annotated[None, Depends(require_organization_admin)],
):
    target = db.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization.id,
        )
    ).first()

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if (
        target.role == OrganizationRole.OWNER
        or data.role == OrganizationRole.OWNER
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Use the ownership-transfer workflow to change ownership.",
        )

    if (
        data.role == OrganizationRole.ADMIN
        and current_membership.role != OrganizationRole.OWNER
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can assign admin privileges.",
        )

    if (
        target.role == OrganizationRole.ADMIN
        and current_membership.role != OrganizationRole.OWNER
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can modify another admin's role.",
        )

    target.role = data.role
    db.add(target)
    db.commit()
    db.refresh(target)

    return target
