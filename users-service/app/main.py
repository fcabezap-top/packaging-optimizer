from fastapi import FastAPI
from .routers import users, auth

app = FastAPI(title="Users Service")

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
def health():
    return {"service": "users", "status": "ok"}