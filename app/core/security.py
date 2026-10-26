from pwdlib import PasswordHash
from datetime import timedelta, datetime, timezone
import jwt

from app.core.config import settings

password_hash = PasswordHash.recommended()

def _create_token(
    data: dict,
    expires_delta: timedelta,
    token_type: str,
) -> str:
    now = datetime.now(timezone.utc)

    payload = data.copy()
    payload.update({
        "iat": now,
        "exp": now + expires_delta,
        "token_type": token_type,
    })

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    return _create_token(
        data=data,
        expires_delta=(
            expires_delta
            if expires_delta is not None
            else timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        ),
        token_type="access",
    )


def create_refresh_token(data: dict) -> str:
    return _create_token(
        data=data,
        expires_delta=timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        ),
        token_type="refresh",
    )


def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        if payload.get("token_type") != "access":
            raise jwt.InvalidTokenError("Expected an access token")

        return payload

    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")
