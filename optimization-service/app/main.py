from contextlib import asynccontextmanager

from fastapi import FastAPI

from .routers import containers, rules, rule_assignments
from .seed import run_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_seed()
    yield


app = FastAPI(title="Optimization Service", lifespan=lifespan)

app.include_router(containers.router)
app.include_router(rules.router)
app.include_router(rule_assignments.router)


@app.get("/")
def health():
    return {"service": "optimization", "status": "ok"}
