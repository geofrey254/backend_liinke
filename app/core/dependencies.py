
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from app.core.security import verify_access_token
from app.database.session import get_session
from app.models.user import User
from app.models.organization import Organization
from app.models.organizationMembership import MembershipStatus, OrganizationMembership



bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_session)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = verify_access_token(credentials.credentials)
        subject = payload.get("sub")

        if not isinstance(subject, str) or not subject.isdigit():
            raise unauthorized

        user_id = int(subject)

    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized from None

    user = db.get(User, user_id)

    if user is None:
        raise unauthorized

    return user

def get_current_organization(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Organization:
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an organization",
        )
    
    organization = db.get(Organization, current_user.organization_id)

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    if not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not active",
        )

    return organization

def get_current_membership(
    current_user: Annotated[User, Depends(get_current_user)],
    organization: Annotated[Organization, Depends(get_current_organization)],
    db: Annotated[Session, Depends(get_session)],
) -> OrganizationMembership:

    statement = select(OrganizationMembership).where(
        OrganizationMembership.user_id == current_user.id,
        OrganizationMembership.organization_id
        == organization.id,
        OrganizationMembership.status == MembershipStatus.ACTIVE
    )

    membership = db.exec(statement).first()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this organization",
        )

    return membership

def require_organization_admin(
    current_membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
) -> None:
    if current_membership.role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have admin privileges in the organization",
        )

def require_organization_owner(
    current_membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
) -> None:
    if current_membership.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have owner privileges in the organization",
        )
