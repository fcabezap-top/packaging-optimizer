from contextlib import asynccontextmanager

from fastapi import FastAPI

from .routers import users, auth
from .seed import run_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_seed()
    yield


app = FastAPI(title="Users Service", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
def health():
    return {"service": "users", "status": "ok"}