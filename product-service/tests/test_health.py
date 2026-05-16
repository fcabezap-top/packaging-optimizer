import os
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient
from jose import jwt

from app.main import app

client = TestClient(app)

SECRET_KEY = os.getenv("SECRET_KEY", "changeme-use-a-long-random-secret-in-production")
ALGORITHM = "HS256"


def _token(role: str, uid: str) -> str:
    payload = {
        "sub": f"ci_{role}",
        "role": role,
        "id": uid,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


TOKEN_REVIEWER     = _token("reviewer",     "00000000-0000-0000-0000-000000000001")
TOKEN_MANUFACTURER = _token("manufacturer", "00000000-0000-0000-0000-000000000002")
TOKEN_ADMIN        = _token("admin",        "00000000-0000-0000-0000-000000000003")


def test_health():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"service": "product", "status": "ok"}


def test_families_requires_auth():
    r = client.get("/families")
    assert r.status_code == 401


def test_families_accessible_with_token():
    r = client.get("/families", headers={"Authorization": f"Bearer {TOKEN_REVIEWER}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_family_requires_admin():
    """Reviewer no puede crear familias — solo admin."""
    r = client.post(
        "/families",
        json={"name": "CI Familia Test", "family_code": 9999},
        headers={"Authorization": f"Bearer {TOKEN_REVIEWER}"},
    )
    assert r.status_code == 403


def test_create_family_as_admin():
    r = client.post(
        "/families",
        json={"name": "CI Familia Test", "family_code": 9998},
        headers={"Authorization": f"Bearer {TOKEN_ADMIN}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "CI Familia Test"
    assert "id" in data


def test_products_requires_auth():
    r = client.get("/products/")
    assert r.status_code == 401


def test_products_accessible_reviewer():
    r = client.get("/products/", headers={"Authorization": f"Bearer {TOKEN_REVIEWER}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_products_mine_manufacturer():
    """Fabricante puede listar sus propios productos."""
    r = client.get("/products/mine", headers={"Authorization": f"Bearer {TOKEN_MANUFACTURER}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_subfamilies_accessible():
    r = client.get("/subfamilies", headers={"Authorization": f"Bearer {TOKEN_REVIEWER}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)