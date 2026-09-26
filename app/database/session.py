from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, create_engine, SQLModel
from app.core.config import settings

engine = create_engine(settings.DATABASE_URI, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]