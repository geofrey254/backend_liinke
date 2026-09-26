from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.v1.router import router as api_v1_router

from app.database.session import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)


app.include_router(api_v1_router, prefix="/api/v1")