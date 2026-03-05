from typing import Optional
from jose import JWTError, jwt
from .config import SECRET_KEY, ALGORITHM


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if not username:
            return None
        return {"username": username, "role": role}
    except JWTError:
        return None
