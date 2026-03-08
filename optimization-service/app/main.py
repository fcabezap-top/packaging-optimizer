import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import containers, rules, rule_assignments, renders
from .seed import run_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_seed()
    yield


app = FastAPI(title="Optimization Service", lifespan=lifespan)

_origins = os.getenv("CORS_ORIGIN", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(containers.router)
app.include_router(rules.router)
app.include_router(rule_assignments.router)
app.include_router(renders.router)


@app.get("/")
def health():
    return {"service": "optimization", "status": "ok"}
