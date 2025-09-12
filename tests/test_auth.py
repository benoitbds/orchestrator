import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.security import get_current_user


def test_get_current_user_existing_user(monkeypatch):
    def fake_verify(token):
        assert token == 'abc'
        return {'uid': 'u1', 'email': 'e@example.com', 'email_verified': True}

    monkeypatch.setattr('backend.app.security.fb_auth.verify_id_token', fake_verify)
    monkeypatch.setattr('orchestrator.crud.get_user_by_uid', lambda uid: {'uid': uid})
    created = []
    monkeypatch.setattr('orchestrator.crud.create_user', lambda **kw: created.append(kw))
    creds = HTTPAuthorizationCredentials(scheme='Bearer', credentials='abc')
    user = get_current_user(creds)
    assert user == {'uid': 'u1', 'email': 'e@example.com', 'email_verified': True}
    assert created == []


def test_get_current_user_missing_token():
    with pytest.raises(HTTPException):
        get_current_user(None)


def test_get_current_user_invalid(monkeypatch):
    def fake_verify(token):
        raise ValueError('bad token')

    monkeypatch.setattr('backend.app.security.fb_auth.verify_id_token', fake_verify)
    creds = HTTPAuthorizationCredentials(scheme='Bearer', credentials='bad')
    with pytest.raises(HTTPException):
        get_current_user(creds)


def test_get_current_user_auto_provisions_admin(monkeypatch):
    def fake_verify(token):
        assert token == 'abc'
        return {'uid': 'u1', 'email': 'admin@example.com'}

    monkeypatch.setattr('backend.app.security.fb_auth.verify_id_token', fake_verify)
    monkeypatch.setattr('orchestrator.crud.get_user_by_uid', lambda uid: None)
    created = {}

    def fake_create_user(uid, email, is_admin):
        created.update({'uid': uid, 'email': email, 'is_admin': is_admin})
        return created

    monkeypatch.setattr('orchestrator.crud.create_user', fake_create_user)
    monkeypatch.setattr('backend.app.security.ADMIN_EMAILS', {'admin@example.com'})
    creds = HTTPAuthorizationCredentials(scheme='Bearer', credentials='abc')
    user = get_current_user(creds)
    assert user['uid'] == 'u1'
    assert created == {'uid': 'u1', 'email': 'admin@example.com', 'is_admin': True}


from fastapi.testclient import TestClient
from api.main import app


def test_projects_route_requires_auth():
    client = TestClient(app)
    r = client.get("/projects")
    assert r.status_code == 401


def test_projects_route_returns_projects(monkeypatch):
    def fake_verify(token):
        assert token == "good"
        return {"uid": "u1", 'email': 'e@example.com'}

    monkeypatch.setattr(
        "backend.app.security.fb_auth.verify_id_token", fake_verify
    )
    monkeypatch.setattr('orchestrator.crud.get_user_by_uid', lambda uid: {'uid': uid})
    monkeypatch.setattr('orchestrator.crud.create_user', lambda uid, email, is_admin: None)
    monkeypatch.setattr("orchestrator.crud.get_projects", lambda: [{"id": 1}])
    client = TestClient(app)
    r = client.get("/projects", headers={"Authorization": "Bearer good"})
    assert r.status_code == 200
    assert r.json() == [{"id": 1}]


def test_projects_route_returns_empty_list(monkeypatch):
    def fake_verify(token):
        assert token == "good"
        return {"uid": "u1", 'email': 'e@example.com'}

    monkeypatch.setattr(
        "backend.app.security.fb_auth.verify_id_token", fake_verify
    )
    monkeypatch.setattr('orchestrator.crud.get_user_by_uid', lambda uid: None)
    created = {}
    monkeypatch.setattr('orchestrator.crud.create_user', lambda uid, email, is_admin: created.update({'uid': uid}))
    monkeypatch.setattr("orchestrator.crud.get_projects", lambda: [])
    client = TestClient(app)
    r = client.get("/projects", headers={"Authorization": "Bearer good"})
    assert r.status_code == 200
    assert r.json() == []
    assert created["uid"] == "u1"
