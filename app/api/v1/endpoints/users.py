@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(data:UserCreate):
    return user_service.create_user(data)