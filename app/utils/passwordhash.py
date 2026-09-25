from app.core.security import password_hash

def hash_password(password:str) -> str:
    return password_hash.hash(password)

def verify_password(password:str, hashed_password:str) -> bool:
    return password_hash.verify(password, hashed_password)