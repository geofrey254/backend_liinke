from sqlmodel import select

from fastapi import HTTPException, status

from app.models.user import User, UserCreate, UserResponse
from app.utils.passwordhash import hash_password
from app.database.session import SessionDep



def create_user_service(user_data: UserCreate, db: SessionDep) -> UserResponse:
    hashed_password = hash_password(user_data.password)

    new_user = User(
        username=user_data.username,
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

def get_users_service(db: SessionDep) -> list[UserResponse]:
    users = db.exec(select(User)).all()
    return users

def get_user_by_id_service(user_id: int, db: SessionDep) -> UserResponse | None:
    user = db.get(User, user_id)

    if not user: 
        raise HTTPException(
            status_code=404,
            detail=f"User with id {user_id} not found"
        )

    return user