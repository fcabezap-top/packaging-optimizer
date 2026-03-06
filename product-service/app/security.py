import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

SECRET_KEY = os.getenv("SECRET_KEY", "changeme-use-a-long-random-secret-in-production")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/auth/login")


class TokenData(BaseModel):
    username: str
    role: str
    id: Optional[str] = None


def _decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        user_id: Optional[str] = payload.get("id")
        if username is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(username=username, role=role, id=user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_auth(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Any authenticated user (any role)."""
    return _decode_token(token)


def require_admin(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Only admin role."""
    data = _decode_token(token)
    if data.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return data


def require_reviewer_or_admin(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Only reviewer or admin."""
    data = _decode_token(token)
    if data.role not in ("admin", "reviewer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer or admin role required",
        )
    return data


def require_content_creator(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Admin, manufacturer or reviewer can create products."""
    data = _decode_token(token)
    if data.role not in ("admin", "manufacturer", "reviewer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return data
