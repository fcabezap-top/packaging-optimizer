import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

_USER = {
    "username": "testuser_ci",
    "email": "testuser_ci@example.com",
    "first_name": "Test",
    "last_name": "CI",
    "password": "Secure1@pass",
    "role": "manufacturer",
}


def test_health():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"service": "users", "status": "ok"}


def test_register_user():
    r = client.post("/auth/register", json=_USER)
    assert r.status_code in (201, 400)  # 400 si ya existe de una ejecucion anterior
    if r.status_code == 201:
        data = r.json()
        assert data["username"] == _USER["username"]
        assert data["role"] == "manufacturer"
        assert "password" not in data


def test_register_weak_password():
    bad = {**_USER, "username": "other_ci", "email": "other_ci@example.com", "password": "weak"}
    r = client.post("/auth/register", json=bad)
    assert r.status_code == 422


def test_login_valid():
    client.post("/auth/register", json=_USER)
    r = client.post("/auth/login", data={"username": _USER["username"], "password": _USER["password"]})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password():
    r = client.post("/auth/login", data={"username": _USER["username"], "password": "WrongPass1!"})
    assert r.status_code == 401


def test_me_with_valid_token():
    client.post("/auth/register", json=_USER)
    login = client.post("/auth/login", data={"username": _USER["username"], "password": _USER["password"]})
    token = login.json()["access_token"]
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == _USER["username"]


def test_me_without_token():
    r = client.get("/users/me")
    assert r.status_code == 401


def test_list_users_requires_reviewer():
    """GET /users/ solo accesible para reviewer/admin."""
    client.post("/auth/register", json=_USER)
    login = client.post("/auth/login", data={"username": _USER["username"], "password": _USER["password"]})
    token = login.json()["access_token"]
    r = client.get("/users/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (403, 401)