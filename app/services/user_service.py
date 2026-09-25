from app.models.user import User, UserCreate, UserResponse
from app.utils.passwordhash import hash_password
from app.database.session import Session


def create_user(user_data: UserCreate, db: Session) -> UserResponse:
    hashed_password = hash_password(user_data.password)

    new_user = User(
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        hashed_password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

def get_users(db: Session) -> list[UserResponse]:
    users = db.exec(User).all()
    return users