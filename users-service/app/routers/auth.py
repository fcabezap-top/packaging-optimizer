import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from pydantic import BaseModel, EmailStr

from ..database import users_collection, reset_tokens_collection
from ..models.user import UserCreate, UserResponse, Token
from ..security import hash_password, verify_password, create_access_token
from ..mailer import send_reset_email
from ..config import RESET_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["Auth"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already taken")

    user_dict = user.dict()
    user_dict["hashed_password"] = hash_password(user_dict.pop("password"))
    users_collection.insert_one(user_dict)

    return UserResponse(**user_dict)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_collection.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({
        "sub": user["username"],
        "role": user["role"],
        "id": user.get("id"),
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
    })
    return {"access_token": token, "token_type": "bearer"}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(body: ForgotPasswordRequest):
    """
    Genera un token de reset y envía el email.
    Siempre responde igual para no revelar si el email existe (anti-enumeración).
    """
    _GENERIC_RESPONSE = {"detail": "Si el email existe, recibirás un correo en breve."}

    user = users_collection.find_one({"email": body.email})
    if not user:
        return _GENERIC_RESPONSE

    # Generar token seguro y guardar solo su hash
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

    # Invalidar tokens anteriores del mismo usuario
    reset_tokens_collection.delete_many({"user_id": str(user.get("id", user["username"]))})

    reset_tokens_collection.insert_one({
        "user_id":    str(user.get("id", user["username"])),
        "username":   user["username"],
        "token_hash": token_hash,
        "expires_at": expires_at,
        "used":       False,
    })

    send_reset_email(body.email, raw_token)
    return _GENERIC_RESPONSE


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(body: ResetPasswordRequest):
    """Valida el token y actualiza la contraseña."""
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()

    record = reset_tokens_collection.find_one({"token_hash": token_hash})

    if not record:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")
    if record.get("used"):
        raise HTTPException(status_code=400, detail="Token ya utilizado")
    if record["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expirado")

    # Validar fortaleza de contraseña reutilizando el validator del modelo
    try:
        from ..models.user import UserCreate
        UserCreate.model_validate({
            "username": "x", "email": "x@x.com", "first_name": "x",
            "last_name": "x", "password": body.new_password, "role": "user"
        })
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    new_hash = hash_password(body.new_password)
    users_collection.update_one(
        {"username": record["username"]},
        {"$set": {"hashed_password": new_hash}}
    )
    reset_tokens_collection.update_one(
        {"token_hash": token_hash},
        {"$set": {"used": True}}
    )

    return {"detail": "Contraseña actualizada correctamente"}
