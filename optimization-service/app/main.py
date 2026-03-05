from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime, timezone

from .security import decode_access_token
from .database import proposals_collection

app = FastAPI(title="Optimization Service")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


class OptimizationRequest(BaseModel):
    items: list[dict]
    container_dimensions: dict


@app.get("/")
def health():
    return {"service": "optimization", "status": "ok"}


@app.post("/optimize")
def optimize(request: OptimizationRequest, current_user: dict = Depends(get_current_user)):
    # Aquí irá la lógica de optimización real
    # Por ahora devolvemos un resultado de ejemplo y lo guardamos
    result = {
        "username": current_user["username"],
        "items": request.items,
        "container_dimensions": request.container_dimensions,
        "status": "computed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    inserted = proposals_collection.insert_one(result.copy())
    result["id"] = str(inserted.inserted_id)
    return result


@app.get("/proposals")
def get_my_proposals(current_user: dict = Depends(get_current_user)):
    proposals = []
    for p in proposals_collection.find({"username": current_user["username"]}):
        p["_id"] = str(p["_id"])
        proposals.append(p)
    return proposals