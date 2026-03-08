import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import users, auth
from .seed import run_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .database import ensure_indexes
    ensure_indexes()
    run_seed()
    yield


app = FastAPI(title="Users Service", lifespan=lifespan)

_origins = os.getenv("CORS_ORIGIN", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
def health():
    return {"service": "users", "status": "ok"}